import { 
  action, 
  KeyDownEvent, 
  SingletonAction, 
  WillAppearEvent,
  WillDisappearEvent
} from "@elgato/streamdeck";

import { ClaudeAPI } from "../claude-api";

@action({ UUID: "de.co.context.claudedeck.escape" })
export class EscapeAction extends SingletonAction {
  private claudeAPI: ClaudeAPI;
  private updateInterval?: NodeJS.Timeout;
  private currentActionId?: string;

  constructor() {
    super();
    this.claudeAPI = new ClaudeAPI();
  }

  override async onWillAppear(ev: WillAppearEvent): Promise<void> {
    // Start real-time state polling
    this.startStatePolling(ev.action.id);
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
    const actions = Array.from(this.actions);
    const action = actions.find(a => a.id === actionId);
    if (!action) return;

    const isConnected = await this.claudeAPI.checkConnection();
    if (!isConnected) {
      await action.setState(1); // Offline state
    } else {
      await action.setState(0); // Active state
    }
  }

  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    // Check if connected before allowing action
    const isConnected = await this.claudeAPI.checkConnection();
    if (!isConnected) {
      await ev.action.showAlert();
      return;
    }

    // Send ESC key (ASCII 27)
    const response = await this.claudeAPI.sendCommand("\x1b");
    
    // Restart polling cycle to avoid race condition
    this.restartStatePolling();
    
    if (response.status !== "sent") {
      await ev.action.showAlert();
    }
    // Let real-time polling handle state updates, no showOk() overlay
  }
}