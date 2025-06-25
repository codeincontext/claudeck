import { 
  action, 
  KeyDownEvent, 
  SingletonAction, 
  WillAppearEvent,
  WillDisappearEvent,
  DidReceiveSettingsEvent,
  PropertyInspectorDidAppearEvent
} from "@elgato/streamdeck";

import { ClaudeAPI, ClaudeState } from "../claude-api";

type CommandSettings = {
  command?: string;
  wrapperUrl?: string;
  showState?: boolean;
  commandHistory?: string[];
}

@action({ UUID: "de.co.context.claudedeck.command" })
export class CommandAction extends SingletonAction<CommandSettings> {
  private claudeAPI: ClaudeAPI;
  private updateInterval?: NodeJS.Timeout;
  private commandHistoryIndex: number = -1;

  constructor() {
    super();
    this.claudeAPI = new ClaudeAPI();
  }

  override async onWillAppear(ev: WillAppearEvent<CommandSettings>): Promise<void> {
    const { command, wrapperUrl, showState } = ev.payload.settings;
    
    // Update API URL if provided
    if (wrapperUrl) {
      this.claudeAPI = new ClaudeAPI(wrapperUrl);
    }

    // Start state polling if enabled (disabled for now)
    // if (showState !== false) {
    //   this.startStatePolling(ev.action.id);
    // }

    // Check connection
    const isConnected = await this.claudeAPI.checkConnection();
    if (!isConnected) {
      await ev.action.showAlert();
      await ev.action.setTitle("Offline");
    }
  }

  override async onWillDisappear(ev: WillDisappearEvent<CommandSettings>): Promise<void> {
    this.stopStatePolling();
  }

  override async onKeyDown(ev: KeyDownEvent<CommandSettings>): Promise<void> {
    const { command = "help" } = ev.payload.settings;
    
    // Visual feedback
    await ev.action.setState(1);
    
    // Send command
    const response = await this.claudeAPI.sendCommand(command);
    
    if (response.status === "sent") {
      // Add to history
      await this.addToHistory(ev, command);
    } else {
      await ev.action.showAlert();
    }
    
    // Reset visual state
    setTimeout(() => ev.action.setState(0), 100);
  }

  override async onDidReceiveSettings(
    ev: DidReceiveSettingsEvent<CommandSettings>
  ): Promise<void> {
    const { wrapperUrl, showState } = ev.payload.settings;
    
    // Update API URL if changed
    if (wrapperUrl && wrapperUrl !== (this.claudeAPI as any).baseUrl) {
      this.claudeAPI = new ClaudeAPI(wrapperUrl);
    }

    // Update state polling (disabled for now)
    // if (showState === false) {
    //   this.stopStatePolling();
    // } else {
    //   this.startStatePolling(ev.action.id);
    // }
  }

  private startStatePolling(actionId: string): void {
    this.stopStatePolling();
    
    // Initial update
    this.updateButtonState(actionId);
    
    // Poll every 2 seconds
    this.updateInterval = setInterval(() => {
      this.updateButtonState(actionId);
    }, 2000);
  }

  private stopStatePolling(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = undefined;
    }
  }

  private async updateButtonState(actionId: string): Promise<void> {
    const state = await this.claudeAPI.getState();
    const action = this.actions.getActionById(actionId);
    if (!action) return;

    if (state) {
      // Update title with mode
      const modeEmoji = this.getModeEmoji(state.mode);
      await action.setTitle(`${modeEmoji} ${state.mode}`);
      
      // Update state based on mode
      if (state.mode === "error" || state.mode === "offline") {
        await action.setState(1); // Error state
      } else {
        await action.setState(0); // Normal state
      }
    } else {
      await action.setTitle("Offline");
      await action.setState(1);
    }
  }

  private getModeEmoji(mode: string): string {
    const modeMap: Record<string, string> = {
      "interactive": "💬",
      "planning": "📋",
      "auto-accept": "🚀",
      "thinking": "🤔",
      "error": "❌",
      "offline": "🔌",
    };
    return modeMap[mode] || "🤖";
  }

  private async addToHistory(
    ev: KeyDownEvent<CommandSettings>,
    command: string
  ): Promise<void> {
    const settings = ev.payload.settings;
    const history = settings.commandHistory || [];
    
    // Remove duplicates and add to front
    const newHistory = [
      command,
      ...history.filter(cmd => cmd !== command)
    ].slice(0, 20); // Keep last 20 commands
    
    await ev.action.setSettings({
      ...settings,
      commandHistory: newHistory
    });
  }
}