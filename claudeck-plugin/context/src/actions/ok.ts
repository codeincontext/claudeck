import { 
  action, 
  KeyDownEvent, 
  SingletonAction, 
  WillAppearEvent,
  WillDisappearEvent
} from "@elgato/streamdeck";

import { ClaudeAPI } from "../claude-api";

@action({ UUID: "de.co.context.claudedeck.ok" })
export class OkAction extends SingletonAction {
  private claudeAPI: ClaudeAPI;
  private updateInterval?: NodeJS.Timeout;
  private currentActionId?: string;

  constructor() {
    super();
    this.claudeAPI = new ClaudeAPI();
  }

  override async onWillAppear(ev: WillAppearEvent): Promise<void> {
    // Check connection
    const isConnected = await this.claudeAPI.checkConnection();
    if (!isConnected) {
      await ev.action.showAlert();
      await ev.action.setTitle("Offline");
    } else {
      // Start state polling
      this.startStatePolling(ev.action.id);
    }
  }

  override async onWillDisappear(ev: WillDisappearEvent): Promise<void> {
    this.stopStatePolling();
  }

  private startStatePolling(actionId: string): void {
    this.currentActionId = actionId;
    this.stopStatePolling();
    
    // Initial update
    this.updateButtonState(actionId);
    
    // Poll every 250ms for near real-time updates
    this.updateInterval = setInterval(() => {
      this.updateButtonState(actionId);
    }, 250);
  }

  private restartStatePolling(): void {
    if (this.currentActionId) {
      this.startStatePolling(this.currentActionId);
    }
  }

  private stopStatePolling(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = undefined;
    }
  }

  private async updateButtonState(actionId: string): Promise<void> {
    const state = await this.claudeAPI.getState();
    const actions = Array.from(this.actions);
    const action = actions.find(a => a.id === actionId);
    if (!action) return;

    if (state) {
      // Check for thinking state
      if (state.mode === "thinking") {
        await action.setState(1); // Thinking/Wait state
      } else {
        await action.setState(0); // Ready/Normal state
      }
    } else {
      await action.setState(2); // Offline state
    }
  }

  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    // Check if connected before allowing action
    const isConnected = await this.claudeAPI.checkConnection();
    if (!isConnected) {
      await ev.action.showAlert();
      return;
    }

    // Send empty command (just carriage return)
    const response = await this.claudeAPI.sendCommand("");
    
    // Restart polling cycle to avoid race condition
    this.restartStatePolling();
    
    if (response.status !== "sent") {
      await ev.action.showAlert();
    }
  }
}