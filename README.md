# Claude Code + Stream Deck Integration

Control Claude Code directly from your Elgato Stream Deck using this PTY wrapper and custom plugin.

## How It Works

1. **PTY Wrapper** (`claude_deck_wrapper.py`) - Creates a pseudo-terminal around Claude Code
2. **HTTP API** - Exposes endpoints for Stream Deck to send commands and get state
3. **Stream Deck Plugin** - Custom plugin that communicates with the wrapper

## Quick Start

### 1. Install Dependencies

```bash
# Make sure Claude Code is installed
npm install -g @anthropic/claude-code

# Python should already be available on macOS
# No additional Python packages needed - uses only stdlib
```

### 2. Start the Wrapper

```bash
cd /Users/adz/Documents/code/claude-deck
python3 claude_deck_wrapper.py
```

This will:
- Start Claude Code in a PTY
- Launch HTTP API on localhost:8080
- Allow normal keyboard interaction with Claude

### 3. Test the API

In another terminal:

```bash
python3 test_wrapper.py
```

This will test the HTTP endpoints and send a sample command.

### 4. Install Stream Deck Plugin

1. Copy the plugin folder to Stream Deck plugins directory:
   ```bash
   cp -r streamdeck-plugin/com.claude.deck.sdPlugin ~/Library/ApplicationSupport/com.elgato.StreamDeck/Plugins/
   ```

2. Restart Stream Deck software

3. Drag "Claude Command" action to a button

4. Configure the command in the property inspector

## API Endpoints

### GET /state
Returns current Claude Code state:
```json
{
  "mode": "interactive",
  "prompt": "> ",
  "options": []
}
```

### POST /command
Send command to Claude:
```bash
curl -X POST http://localhost:8080/command \\
  -H "Content-Type: application/json" \\
  -d '{"command": "help"}'
```

## Predefined Commands

The Stream Deck plugin includes these common commands:

- `help` - Show Claude help
- `/plan` - Enter planning mode  
- `/auto` - Toggle auto-accept mode
- `/reset` - Reset conversation
- `/exit` - Exit Claude
- `y` - Yes response
- `n` - No response
- `q` - Quit/Cancel

## Architecture

```
Stream Deck → Plugin (JS) → HTTP API → PTY Wrapper → Claude Code
                ↑                         ↓
              Button Press              Terminal I/O
```

## Troubleshooting

### Wrapper won't start
- Ensure `claude` command is in PATH
- Check if port 8080 is available

### Stream Deck plugin not working  
- Verify wrapper is running on localhost:8080
- Check Stream Deck console for errors
- Restart Stream Deck software

### Commands not working
- Test API directly with `test_wrapper.py`
- Check wrapper console output
- Verify Claude Code is responding

## Development

### Testing Without Stream Deck

```bash
# Send commands via curl
curl -X POST http://localhost:8080/command -H "Content-Type: application/json" -d '{"command": "help"}'

# Check state
curl http://localhost:8080/state
```

### Extending Commands

Add new commands in the property inspector (`propertyinspector.html`) preset list, or create custom commands by typing directly into the command field.

### State Detection

The wrapper parses Claude's terminal output to detect:
- Current mode (planning, auto-accept, interactive)
- Available options
- Current prompt

Extend `ClaudeState.parse_output()` to detect additional patterns.