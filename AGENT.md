# Claudeck

Stream Deck integration for Claude Code - control Claude directly from your Stream Deck with custom buttons and dynamic state awareness.

## What is Claudeck?

Claudeck provides a seamless way to control Claude Code from your Elgato Stream Deck. It consists of:

- **Stream Deck Plugin**: TypeScript-based plugin with 4 dedicated actions
- **Python Wrapper**: PTY-based wrapper that bridges Stream Deck and Claude Code
- **Dynamic State Awareness**: Buttons change icons and labels based on Claude's current mode

## Features

### Stream Deck Actions

- **OK Button**: Send Return/Enter key (checkmark icon)
- **Escape Button**: Send Escape key (cross icon) 
- **Mode Button**: Switches between plan, auto-accept, and normal modes
- **Command Button**: Send custom freetext commands

### Dynamic State Awareness

The Shift+Tab button automatically adapts based on Claude Code's mode:
- **Plan Mode**: Shows plan icon with "Plan" label
- **Auto-Accept Mode**: Shows auto-accept icon with "Auto" label  
- **Normal Mode**: Shows default icon with "Normal" label
- **Offline**: Grayed out with "Offline" label

### Smart Input Handling

- Properly handles Claude Code's inquirer.js-based input system
- Sends correct key sequences for macOS terminal interaction
- Separate command and carriage return handling for reliable execution
- Connection checking prevents actions when Claude Code is offline

## Installation

### Prerequisites

- Elgato Stream Deck software
- Claude Code installed and available in PATH
- Node.js and npm (for Stream Deck plugin development)
- Python 3.9+ with uv package manager (targets modern Python features)

### Install the Python Wrapper

```bash
# Clone or download the repository
cd claudeck

# Install globally with uv (development mode for easy updates)
uv tool install --editable .
```

This makes the `claudeck` command available globally in your PATH.

### Install the Stream Deck Plugin

1. Install Stream Deck CLI tools:
   ```bash
   npm install -g @elgato/cli
   ```

2. Build and install the plugin:
   ```bash
   cd claudeck-plugin/context
   npm install
   npm run build
   streamdeck link .
   ```

## Stream Deck CLI Commands

```bash
streamdeck [options] [command]

Options:
  -v                            display CLI version
  -h, --help                    display help for command

Commands:
  create                        Stream Deck plugin creation wizard
  link [path]                   Links the plugin to Stream Deck
  restart|r <uuid>              Starts the plugin in Stream Deck; if already running, stops first
  stop|s <uuid>                 Stops the plugin in Stream Deck
  dev [options]                 Enables developer mode
  validate [options] [path]     Validates the Stream Deck plugin
  pack|bundle [options] [path]  Creates a .streamDeckPlugin file from the plugin
  config                        Manage the local configuration
  help [command]                Display help for command

# Common commands for development:
streamdeck restart de.co.context.claudedeck    # Restart plugin after changes
streamdeck link .                              # Link plugin from current directory
streamdeck validate                            # Check plugin validity
```

## Usage

### Starting the Wrapper

Navigate to any project directory and run:

```bash
claudeck
```

This starts:
- Claude Code in the current directory (uses PWD for project context)
- HTTP API server on port 8080 for Stream Deck communication
- State monitoring for dynamic button updates

### Using Stream Deck Buttons

1. **Drag Actions**: Add Claude Deck actions to your Stream Deck from the Actions panel
2. **OK Button**: Press for confirmations, continuing prompts
3. **Escape Button**: Press to cancel operations, go back
4. **Shift+Tab Button**: Context-sensitive alternative actions
5. **Command Button**: Configure custom commands in Property Inspector

### Command Examples

Popular commands to configure in the Command action:
- `/help` - Show Claude Code help
- `/plan` - Enter planning mode  
- `/auto` - Toggle auto-accept mode
- `git status` - Check git status
- `npm test` - Run tests

## Architecture

### Communication Flow

```
Stream Deck → HTTP API → Python PTY Wrapper → Claude Code
```

1. **Stream Deck Plugin** sends HTTP requests to localhost:8080
2. **Python Wrapper** receives commands and forwards to Claude Code via PTY
3. **Claude Code** runs in pseudo-terminal with proper TTY handling
4. **State Monitoring** tracks Claude's mode for dynamic button updates

### Key Technical Features

- **PTY Integration**: Proper pseudo-terminal setup for Claude Code
- **inquirer.js Compatibility**: Handles Claude's terminal input requirements
- **Escape Sequence Support**: Properly sends Esc and Shift+Tab key sequences
- **Advanced State Detection**: Pattern-based parsing of Claude's UI output for precise mode detection
- **Real-time Monitoring**: Live terminal output analysis with detailed debug logging
- **Modern Python**: Leverages Python 3.9+ features including dictionary merge operators
- **Connection Management**: Graceful handling of offline states

## Development

### Plugin Development

```bash
cd claudeck-plugin/context

# Install dependencies
npm install

# Build plugin
npm run build

# Restart plugin during development
streamdeck restart de.co.context.claudedeck
```

### Wrapper Development

The wrapper is installed in development mode, so changes to `claude_deck_wrapper.py` take effect immediately without reinstalling.

### Adding New Actions

1. Create new action class in `src/actions/`
2. Add action to `manifest.json` with UUID and icons
3. Register action in `src/plugin.ts`
4. Build and restart plugin

## Troubleshooting

### Stream Deck Plugin Issues

- **Buttons show "Offline"**: Check if `claudeck` wrapper is running
- **Commands not executing**: Restart the Python wrapper
- **Plugin not loading**: Check Stream Deck logs in plugin folder

### Python Wrapper Issues

- **"claude command not found"**: Ensure Claude Code is installed and in PATH
- **Port 8080 in use**: Use `--port` flag to specify different port
- **PTY errors**: Check terminal permissions and environment

### Common Solutions

```bash
# Restart wrapper
pkill -f claude_deck_wrapper
claudeck

# Restart Stream Deck plugin
streamdeck restart de.co.context.claudedeck

# Check if Claude Code is available
which claude
claude --version
```

## Configuration

### Wrapper Options

```bash
claudeck --help
claudeck --port 8080 --quiet
```

### Property Inspector

Configure Command actions through Stream Deck's Property Inspector:
- **Command**: Set custom command text
- **Wrapper URL**: Change API endpoint (default: http://localhost:8080)
- **Show State**: Enable/disable state polling (disabled by default)

## Contributing

### Project Structure

```
claudeck/
├── claude_deck_wrapper.py      # Python PTY wrapper
├── pyproject.toml              # Python package configuration
├── claudeck-plugin/      # Stream Deck plugin
│   └── context/
│       ├── src/                # TypeScript source
│       ├── de.co.context.claudedeck.sdPlugin/  # Built plugin
│       └── package.json        # Node.js dependencies
└── icons/                      # Custom button icons
```

### Making Changes

1. **Wrapper Changes**: Edit `claude_deck_wrapper.py` - changes take effect immediately
2. **Plugin Changes**: Edit TypeScript files, run `npm run build`, restart plugin
3. **Icon Changes**: Replace PNG files in plugin's `imgs/actions/` folders

## License

This project is open source. Feel free to modify and distribute.

## Credits

- Built for Elgato Stream Deck
- Integrates with Anthropic's Claude Code
- Uses modern Stream Deck SDK v2 with TypeScript
- PTY handling inspired by terminal emulation best practices