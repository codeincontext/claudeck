# Stream Deck Plugin Rebuild Plan for Claude Deck

## Overview
This document outlines a complete rebuild of the Claude Deck Stream Deck plugin using the modern Stream Deck SDK. The goal is to create a robust, TypeScript-based plugin that communicates with the existing Python PTY wrapper to control Claude Code.

## Current Architecture Analysis

### What Works
- **Python PTY Wrapper** (`claude_deck_wrapper.py`): Successfully wraps Claude Code in a pseudo-terminal and exposes HTTP endpoints
- **HTTP API**: 
  - `GET /state` - Returns Claude's current state (mode, prompt, options)
  - `POST /command` - Sends commands to Claude
- **Core Functionality**: The wrapper can receive commands and relay them to Claude Code

### What Needs Improvement
- **Plugin Structure**: Current plugin uses outdated JavaScript approach without proper SDK integration
- **No TypeScript**: Missing type safety and modern development features
- **Limited Error Handling**: Plugin doesn't gracefully handle wrapper disconnections
- **No Visual Feedback**: Missing proper icons and state indicators
- **Manual Installation**: No proper build/packaging process

## Technical Requirements

### Prerequisites
- Node.js 20+ (Stream Deck SDK requirement)
- Stream Deck 6.4+ 
- Stream Deck CLI (`@elgato/cli`)
- Visual Studio Code (recommended)
- Python 3.x (for the wrapper)

### Plugin Architecture
```
Stream Deck App ←→ WebSocket ←→ Plugin (Node.js) ←→ HTTP ←→ Python Wrapper ←→ Claude Code
```

## Implementation Plan

### Phase 1: Environment Setup

#### 1.1 Install Stream Deck CLI
```bash
npm install -g @elgato/cli
```

#### 1.2 Create New Plugin Structure
```bash
cd /Users/adz/Documents/code/claude-deck
mkdir claude-deck-plugin-v2
cd claude-deck-plugin-v2
streamdeck create
```

CLI Wizard Inputs:
- **Plugin Name**: Claude Deck
- **Plugin Identifier**: com.claudedeck.controller
- **Author**: Claude Deck Team
- **Description**: Control Claude Code from your Stream Deck
- **Plugin Type**: Custom (Node.js backend)

### Phase 2: Core Plugin Development

#### 2.1 Project Structure
```
claude-deck-plugin-v2/
├── com.claudedeck.controller.sdPlugin/
│   ├── bin/                    # Compiled Node.js code
│   ├── imgs/                   # Plugin icons
│   │   ├── actions/
│   │   │   ├── command/
│   │   │   │   ├── action@2x.png (144x144)
│   │   │   │   └── action.png (72x72)
│   │   ├── plugin/
│   │   │   ├── marketplace@2x.png (144x144)
│   │   │   └── marketplace.png (72x72)
│   │   └── icons/
│   │       ├── checked.png
│   │       └── unchecked.png
│   ├── ui/                     # Property inspector
│   │   ├── command-pi.html
│   │   └── css/
│   └── manifest.json
├── src/
│   ├── actions/
│   │   └── command.ts
│   ├── plugin.ts
│   └── claude-api.ts
├── package.json
├── tsconfig.json
└── README.md
```

#### 2.2 Manifest Configuration
```json
{
  "Actions": [
    {
      "Icon": "imgs/actions/command/action",
      "Name": "Claude Command",
      "PropertyInspectorPath": "ui/command-pi.html",
      "States": [
        {
          "Image": "imgs/actions/command/action",
          "TitleAlignment": "middle",
          "FontSize": "16",
          "TitleColor": "#ffffff",
          "Title": "Claude"
        }
      ],
      "SupportedInMultiActions": true,
      "Tooltip": "Send a command to Claude Code",
      "UUID": "com.claudedeck.controller.command",
      "Controllers": ["Keypad"],
      "Encoder": {
        "TriggerDescription": {
          "Rotate": "Scroll through command history",
          "Push": "Send command",
          "Touch": "Show current state"
        }
      }
    }
  ],
  "SDKVersion": 2,
  "Author": "Claude Deck Team",
  "CodePath": "bin/plugin.js",
  "Description": "Control Claude Code from your Stream Deck",
  "Name": "Claude Deck",
  "Icon": "imgs/plugin/marketplace",
  "URL": "https://github.com/your-repo/claude-deck",
  "Version": "2.0.0",
  "Software": {
    "MinimumVersion": "6.4"
  },
  "OS": [
    {
      "Platform": "mac",
      "MinimumVersion": "10.15"
    },
    {
      "Platform": "windows",
      "MinimumVersion": "10"
    }
  ],
  "Category": "Claude Deck",
  "CategoryIcon": "imgs/plugin/marketplace",
  "Nodejs": {
    "Version": "20",
    "Debug": "enabled"
  }
}
```

#### 2.3 Core Plugin Implementation

**src/plugin.ts**
```typescript
import streamDeck, { LogLevel } from "@elgato/streamdeck";
import { CommandAction } from "./actions/command";

// Configure logging
streamDeck.logger.setLevel(LogLevel.DEBUG);

// Register actions
streamDeck.actions.registerAction(new CommandAction());

// Connect to Stream Deck
streamDeck.connect();
```

**src/claude-api.ts**
```typescript
export interface ClaudeState {
  mode: string;
  prompt: string;
  options: string[];
}

export interface CommandResponse {
  status: "sent" | "failed";
  command: string;
}

export class ClaudeAPI {
  private baseUrl: string;
  private isConnected: boolean = false;

  constructor(url: string = "http://localhost:8080") {
    this.baseUrl = url;
  }

  async checkConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/state`);
      this.isConnected = response.ok;
      return this.isConnected;
    } catch (error) {
      this.isConnected = false;
      return false;
    }
  }

  async getState(): Promise<ClaudeState | null> {
    try {
      const response = await fetch(`${this.baseUrl}/state`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Failed to get Claude state:", error);
      return null;
    }
  }

  async sendCommand(command: string): Promise<CommandResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Failed to send command:", error);
      return { status: "failed", command };
    }
  }
}
```

**src/actions/command.ts**
```typescript
import streamDeck, {
  Action,
  KeyDownEvent,
  SingletonAction,
  WillAppearEvent,
  WillDisappearEvent,
  DidReceiveSettingsEvent,
  PropertyInspectorDidAppearEvent,
  EncoderDownEvent,
  DialRotateEvent,
} from "@elgato/streamdeck";

import { ClaudeAPI, ClaudeState } from "../claude-api";

interface CommandSettings {
  command?: string;
  wrapperUrl?: string;
  showState?: boolean;
  commandHistory?: string[];
}

@SingletonAction
export class CommandAction extends Action {
  private claudeAPI: ClaudeAPI;
  private updateInterval?: NodeJS.Timeout;
  private commandHistoryIndex: number = -1;

  constructor() {
    super("com.claudedeck.controller.command");
    this.claudeAPI = new ClaudeAPI();
  }

  async onWillAppear(ev: WillAppearEvent<CommandSettings>): Promise<void> {
    const { command, wrapperUrl, showState } = ev.payload.settings;
    
    // Update API URL if provided
    if (wrapperUrl) {
      this.claudeAPI = new ClaudeAPI(wrapperUrl);
    }

    // Start state polling if enabled
    if (showState !== false) {
      this.startStatePolling(ev.context);
    }

    // Check connection
    const isConnected = await this.claudeAPI.checkConnection();
    if (!isConnected) {
      await ev.showAlert();
      await ev.setTitle("Offline");
    }
  }

  async onWillDisappear(ev: WillDisappearEvent<CommandSettings>): Promise<void> {
    this.stopStatePolling();
  }

  async onKeyDown(ev: KeyDownEvent<CommandSettings>): Promise<void> {
    const { command = "help" } = ev.payload.settings;
    
    // Visual feedback
    await ev.setState(1);
    
    // Send command
    const response = await this.claudeAPI.sendCommand(command);
    
    if (response.status === "sent") {
      await ev.showOk();
      // Add to history
      await this.addToHistory(ev, command);
    } else {
      await ev.showAlert();
    }
    
    // Reset visual state
    setTimeout(() => ev.setState(0), 100);
  }

  async onDialRotate(ev: DialRotateEvent<CommandSettings>): Promise<void> {
    const { commandHistory = [] } = ev.payload.settings;
    if (commandHistory.length === 0) return;

    // Update history index based on rotation
    if (ev.payload.ticks > 0) {
      this.commandHistoryIndex = Math.min(
        this.commandHistoryIndex + 1,
        commandHistory.length - 1
      );
    } else {
      this.commandHistoryIndex = Math.max(0, this.commandHistoryIndex - 1);
    }

    // Update current command
    const selectedCommand = commandHistory[this.commandHistoryIndex];
    await ev.setSettings({ 
      ...ev.payload.settings,
      command: selectedCommand 
    });
    
    // Show command on button
    await ev.setTitle(selectedCommand);
  }

  async onEncoderDown(ev: EncoderDownEvent<CommandSettings>): Promise<void> {
    // Trigger same as key down
    await this.onKeyDown(ev as any);
  }

  async onPropertyInspectorDidAppear(
    ev: PropertyInspectorDidAppearEvent<CommandSettings>
  ): Promise<void> {
    // Send current state to property inspector
    const state = await this.claudeAPI.getState();
    await ev.sendToPropertyInspector({ 
      type: "state-update",
      state,
      isConnected: await this.claudeAPI.checkConnection()
    });
  }

  async onDidReceiveSettings(
    ev: DidReceiveSettingsEvent<CommandSettings>
  ): Promise<void> {
    const { wrapperUrl, showState } = ev.payload.settings;
    
    // Update API URL if changed
    if (wrapperUrl && wrapperUrl !== this.claudeAPI["baseUrl"]) {
      this.claudeAPI = new ClaudeAPI(wrapperUrl);
    }

    // Update state polling
    if (showState === false) {
      this.stopStatePolling();
    } else {
      this.startStatePolling(ev.context);
    }
  }

  private startStatePolling(context: string): void {
    this.stopStatePolling();
    
    // Initial update
    this.updateButtonState(context);
    
    // Poll every 2 seconds
    this.updateInterval = setInterval(() => {
      this.updateButtonState(context);
    }, 2000);
  }

  private stopStatePolling(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = undefined;
    }
  }

  private async updateButtonState(context: string): Promise<void> {
    const action = streamDeck.actions.getActionById(context);
    if (!action) return;

    const state = await this.claudeAPI.getState();
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
    ev: WillAppearEvent<CommandSettings>,
    command: string
  ): Promise<void> {
    const settings = ev.payload.settings;
    const history = settings.commandHistory || [];
    
    // Remove duplicates and add to front
    const newHistory = [
      command,
      ...history.filter(cmd => cmd !== command)
    ].slice(0, 20); // Keep last 20 commands
    
    await ev.setSettings({
      ...settings,
      commandHistory: newHistory
    });
  }
}
```

#### 2.4 Property Inspector UI

**com.claudedeck.controller.sdPlugin/ui/command-pi.html**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Claude Command Settings</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/elgatosf/streamdeck-plugin-sdk@latest/dist/css/property-inspector.css">
</head>
<body>
  <div class="sdpi-wrapper">
    <!-- Command Input -->
    <div class="sdpi-item">
      <div class="sdpi-item-label">Command</div>
      <input class="sdpi-item-value" type="text" id="command" placeholder="Enter command...">
    </div>

    <!-- Preset Commands -->
    <div class="sdpi-item">
      <div class="sdpi-item-label">Quick Commands</div>
      <select class="sdpi-item-value" id="presets">
        <option value="">Select preset...</option>
        <optgroup label="Navigation">
          <option value="help">Show Help</option>
          <option value="/plan">Planning Mode</option>
          <option value="/auto">Auto-accept Mode</option>
          <option value="/reset">Reset Conversation</option>
          <option value="/exit">Exit Claude</option>
        </optgroup>
        <optgroup label="Responses">
          <option value="y">Yes</option>
          <option value="n">No</option>
          <option value="q">Quit/Cancel</option>
          <option value="c">Continue</option>
        </optgroup>
        <optgroup label="Code Actions">
          <option value="npm test">Run Tests</option>
          <option value="git status">Git Status</option>
          <option value="git diff">Git Diff</option>
        </optgroup>
      </select>
    </div>

    <!-- Advanced Settings -->
    <details>
      <summary>Advanced Settings</summary>
      
      <!-- Wrapper URL -->
      <div class="sdpi-item">
        <div class="sdpi-item-label">Wrapper URL</div>
        <input class="sdpi-item-value" type="text" id="wrapperUrl" 
               placeholder="http://localhost:8080" value="http://localhost:8080">
      </div>

      <!-- Show State -->
      <div class="sdpi-item">
        <div class="sdpi-item-label">Show State on Button</div>
        <input class="sdpi-item-value" type="checkbox" id="showState" checked>
      </div>
    </details>

    <!-- Connection Status -->
    <div class="sdpi-item">
      <div class="sdpi-item-label">Status</div>
      <div class="sdpi-item-value" id="status">Checking...</div>
    </div>

    <!-- Claude State -->
    <div class="sdpi-item" id="stateInfo" style="display: none;">
      <div class="sdpi-item-label">Claude Mode</div>
      <div class="sdpi-item-value" id="claudeMode">Unknown</div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/gh/elgatosf/streamdeck-plugin-sdk@latest/dist/property-inspector.js"></script>
  <script>
    // Property Inspector Logic
    $PI.onConnected((jsn) => {
      const settings = jsn.actionInfo.payload.settings;
      
      // Load saved settings
      document.getElementById('command').value = settings.command || '';
      document.getElementById('wrapperUrl').value = settings.wrapperUrl || 'http://localhost:8080';
      document.getElementById('showState').checked = settings.showState !== false;
      
      // Save on change
      ['command', 'wrapperUrl'].forEach(id => {
        document.getElementById(id).addEventListener('input', updateSettings);
      });
      
      document.getElementById('showState').addEventListener('change', updateSettings);
      
      // Preset handler
      document.getElementById('presets').addEventListener('change', (e) => {
        if (e.target.value) {
          document.getElementById('command').value = e.target.value;
          updateSettings();
          e.target.value = '';
        }
      });
    });

    // Handle messages from plugin
    $PI.onDidReceivePropertyInspectorMessage((message) => {
      if (message.type === 'state-update') {
        updateStatus(message.isConnected, message.state);
      }
    });

    function updateSettings() {
      const settings = {
        command: document.getElementById('command').value,
        wrapperUrl: document.getElementById('wrapperUrl').value,
        showState: document.getElementById('showState').checked
      };
      $PI.setSettings(settings);
    }

    function updateStatus(isConnected, state) {
      const statusEl = document.getElementById('status');
      const stateInfoEl = document.getElementById('stateInfo');
      const modeEl = document.getElementById('claudeMode');
      
      if (isConnected && state) {
        statusEl.textContent = 'Connected';
        statusEl.style.color = '#00ff00';
        stateInfoEl.style.display = 'flex';
        modeEl.textContent = state.mode;
      } else {
        statusEl.textContent = 'Disconnected';
        statusEl.style.color = '#ff0000';
        stateInfoEl.style.display = 'none';
      }
    }
  </script>
</body>
</html>
```

### Phase 3: Visual Assets

#### 3.1 Icon Requirements
- **Action Icons**: 72x72 and 144x144 pixels (@2x for Retina)
- **Plugin Icons**: Same sizes for marketplace
- **State Icons**: Different colors/styles for different Claude modes

#### 3.2 Icon Design Suggestions
- Use Claude's brand colors (if available)
- Clear, simple iconography
- Different states: normal, active, error, offline
- Consider dark/light mode compatibility

### Phase 4: Build and Testing

#### 4.1 Development Commands
```bash
# Install dependencies
npm install

# Build plugin
npm run build

# Watch mode for development
npm run watch

# Link plugin for testing
streamdeck link
```

#### 4.2 Testing Checklist
- [ ] Wrapper is running (`python3 claude_deck_wrapper.py`)
- [ ] Plugin appears in Stream Deck app
- [ ] Commands are sent successfully
- [ ] State updates work
- [ ] Property inspector saves settings
- [ ] Error states handled gracefully
- [ ] Reconnection works after wrapper restart
- [ ] Encoder/dial support functions

### Phase 5: Distribution

#### 5.1 Package Plugin
```bash
streamdeck pack
```

#### 5.2 Distribution Options
1. **Direct Distribution**: Share the `.streamDeckPlugin` file
2. **GitHub Releases**: Automated builds with Actions
3. **Elgato Marketplace**: Submit for official distribution

## Migration Guide

### For Users
1. Uninstall old plugin from Stream Deck
2. Install new `.streamDeckPlugin` file
3. Reconfigure buttons with saved commands
4. Enjoy improved stability and features

### For Developers
1. Archive old plugin code
2. Follow new TypeScript structure
3. Use Stream Deck CLI for all operations
4. Implement proper error handling

## Future Enhancements

### Version 2.1
- [ ] Multi-action support (macro commands)
- [ ] Command templates with variables
- [ ] Integration with Claude's file operations
- [ ] Custom icon per command

### Version 2.2
- [ ] Command history search
- [ ] Conditional commands based on state
- [ ] Profile switching
- [ ] Touch Bar support (Mac)

### Version 3.0
- [ ] Direct PTY integration (remove Python wrapper)
- [ ] Two-way communication display
- [ ] Voice command support
- [ ] AI-suggested commands

## Troubleshooting Guide

### Common Issues

#### Plugin Not Appearing
- Verify Stream Deck 6.4+ installed
- Check plugin was linked: `streamdeck list`
- Restart Stream Deck app

#### Commands Not Working
- Ensure wrapper is running
- Check wrapper URL in settings
- Verify no firewall blocking localhost:8080
- Check wrapper console for errors

#### State Not Updating
- Enable "Show State" in property inspector
- Check network connectivity
- Verify wrapper `/state` endpoint works

## Resources

- [Stream Deck SDK Documentation](https://docs.elgato.com/streamdeck/sdk/)
- [Stream Deck Plugin Samples](https://github.com/elgatosf/streamdeck-plugin-samples)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)

## Conclusion

This rebuild plan provides a modern, maintainable foundation for the Claude Deck Stream Deck plugin. By following Stream Deck SDK best practices and using TypeScript, we ensure better reliability, easier debugging, and future extensibility.

The modular architecture allows for easy additions of new features while maintaining compatibility with the existing Python wrapper. This approach provides immediate value while leaving room for future direct integration possibilities.