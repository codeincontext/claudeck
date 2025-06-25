import { 
  action, 
  KeyDownEvent, 
  SingletonAction, 
  WillAppearEvent,
  WillDisappearEvent
} from "@elgato/streamdeck";

import { ClaudeAPI } from "../claude-api";

@action({ UUID: "de.co.context.claudedeck.shifttab" })
export class ShiftTabAction extends SingletonAction {
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
      // Start state polling for dynamic behavior
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

    if (state && state.button_config) {
      const config = state.button_config;
      
      // Update button title
      await action.setTitle(config.shift_tab_label);
      
      // Map mode to state for icon switching
      switch (state.mode) {
        case "plan":
          await action.setState(1); // Plan icon state
          break;
        case "auto-accept":
          await action.setState(2); // Auto-accept icon state
          break;
        case "exit-confirm":
        case "error":
          await action.setState(3); // Warning/error state
          break;

        default:
          await action.setState(0); // Default state
          break;
      }
      
      // TODO: Could also use config.context_hint for tooltips or status
      // TODO: Could respect config.shift_tab_enabled to disable button
    } else {
      await action.setTitle("Offline");
      await action.setState(3); // Offline state
    }
  }

  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    // Check if connected before allowing action
    const isConnected = await this.claudeAPI.checkConnection();
    if (!isConnected) {
      await ev.action.showAlert();
      return;
    }

    // Send Shift+Tab sequence (ESC[Z)
    const response = await this.claudeAPI.sendCommand("\x1b[Z");
    
    // Restart polling cycle to avoid race condition
    this.restartStatePolling();
    
    if (response.status !== "sent") {
      await ev.action.showAlert();
    }
    // Let real-time polling handle state updates, no showOk() overlay
  }
}