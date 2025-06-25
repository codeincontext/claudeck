import { 
  action, 
  KeyDownEvent, 
  SingletonAction, 
  WillAppearEvent,
  WillDisappearEvent,
  DidReceiveSettingsEvent
} from "@elgato/streamdeck";

import { ClaudeAPI } from "../claude-api";

type ModelSettings = {
  currentModel?: "default" | "opus" | "unknown";
  wrapperUrl?: string;
}

@action({ UUID: "de.co.context.claudedeck.model" })
export class ModelAction extends SingletonAction<ModelSettings> {
  private claudeAPI: ClaudeAPI;
  private updateInterval?: NodeJS.Timeout;
  private currentActionId?: string;

  constructor() {
    super();
    this.claudeAPI = new ClaudeAPI();
  }

  override async onWillAppear(ev: WillAppearEvent<ModelSettings>): Promise<void> {
    const { wrapperUrl, currentModel = "unknown" } = ev.payload.settings;
    
    console.log(`[Model Action] onWillAppear - currentModel: ${currentModel}`);
    console.log(`[Model Action] onWillAppear - full settings:`, ev.payload.settings);
    
    // Update API URL if provided
    if (wrapperUrl) {
      this.claudeAPI = new ClaudeAPI(wrapperUrl);
    }

    // Check connection
    const isConnected = await this.claudeAPI.checkConnection();
    console.log(`[Model Action] onWillAppear - isConnected: ${isConnected}`);
    
    if (!isConnected) {
      console.log(`[Model Action] onWillAppear - setting offline state (3)`);
      await ev.action.setState(3); // Offline state
    } else {
      console.log(`[Model Action] onWillAppear - updating button state for: ${currentModel}`);
      await this.updateButtonState(ev, currentModel);
      // Start polling for model changes
      this.startPolling(ev.action.id);
    }
  }

  override async onWillDisappear(ev: WillDisappearEvent<ModelSettings>): Promise<void> {
    this.stopPolling();
  }

  private startPolling(actionId: string): void {
    this.currentActionId = actionId;
    this.stopPolling();
    
    // Poll every 500ms for model changes
    this.updateInterval = setInterval(() => {
      this.updateFromState(actionId);
    }, 500);
  }

  private stopPolling(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = undefined;
    }
  }

  private async updateFromState(actionId: string): Promise<void> {
    const state = await this.claudeAPI.getState();
    const actions = Array.from(this.actions);
    const action = actions.find(a => a.id === actionId);
    if (!action) return;

    if (state && state.model && state.model !== "unknown") {
      // Update button to match current model
      await this.updateButtonState({ action } as any, state.model);
    } else if (!state) {
      // Offline
      await action.setState(3);
    }
  }

  override async onKeyDown(ev: KeyDownEvent<ModelSettings>): Promise<void> {
    const { currentModel = "unknown" } = ev.payload.settings;
    
    console.log(`[Model Action] Key pressed. Current model: ${currentModel}`);
    
    // Toggle logic: if unknown or default, switch to opus; if opus, switch to default
    const nextModel: "default" | "opus" = 
      currentModel === "opus" ? "default" : "opus";
    
    console.log(`[Model Action] Toggling from ${currentModel} to ${nextModel}`);
    
    // Build the model command
    const command = `/model ${nextModel}`;
    
    console.log(`[Model Action] Sending command: ${command}`);
    
    // Send command
    const response = await this.claudeAPI.sendCommand(command);
    
    console.log(`[Model Action] Command response status: ${response.status}`);
    
    if (response.status === "sent") {
      // Update stored model state
      await ev.action.setSettings({
        ...ev.payload.settings,
        currentModel: nextModel
      });
      
      console.log(`[Model Action] Settings updated with currentModel: ${nextModel}`);
      
      // Update button state and title
      await this.updateButtonState(ev, nextModel);
    } else {
      console.log(`[Model Action] Command failed, showing offline state`);
      await ev.action.showAlert();
      await ev.action.setState(3); // Show offline state
    }
  }

  override async onDidReceiveSettings(
    ev: DidReceiveSettingsEvent<ModelSettings>
  ): Promise<void> {
    const { wrapperUrl, currentModel = "unknown" } = ev.payload.settings;
    
    // Update API URL if changed
    if (wrapperUrl && wrapperUrl !== (this.claudeAPI as any).baseUrl) {
      this.claudeAPI = new ClaudeAPI(wrapperUrl);
    }

    // Update button state based on current model
    await this.updateButtonState(ev, currentModel);
  }

  private async updateButtonState(
    ev: WillAppearEvent<ModelSettings> | KeyDownEvent<ModelSettings> | DidReceiveSettingsEvent<ModelSettings>, 
    currentModel: "default" | "opus" | "unknown"
  ): Promise<void> {
    let state: number;
    
    // Debug logging
    console.log(`[Model Action] Updating button state for model: ${currentModel}`);
    
    switch (currentModel) {
      case "default":
        state = 1; // Sonnet/Default state  
        console.log(`[Model Action] Setting state to 1 (Sonnet/Default)`);
        break;
      case "opus":
        state = 2; // Opus state
        console.log(`[Model Action] Setting state to 2 (Opus)`);
        break;
      case "unknown":
      default:
        state = 0; // Unknown state
        console.log(`[Model Action] Setting state to 0 (Unknown)`);
        break;
    }
    
    await ev.action.setState(state);
  }
}
