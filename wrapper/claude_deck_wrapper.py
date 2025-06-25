#!/usr/bin/env python3
"""
Claude Code + Stream Deck PTY Wrapper

Focuses on basic functionality without complex terminal handling.
"""

import os
import pty
import select
import sys
import threading
import json
import time
import socket
import termios
import tty
import signal
import struct
import fcntl
from typing import Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class ClaudeState:
    """Tracks Claude Code's current UI state by parsing terminal output."""
    
    def __init__(self):
        self.mode = "unknown"
        self.model = "unknown"
        self.current_prompt = ""
        self.buffer = ""
        self.last_update = time.time()
    
    def parse_output(self, data: bytes) -> None:
        """Parse terminal output to extract current state."""
        text = data.decode('utf-8', errors='ignore')
        self.buffer += text
        self.last_update = time.time()
        
        # Keep only last 2000 chars to capture mode indicators
        if len(self.buffer) > 2000:
            self.buffer = self.buffer[-2000:]
        
        # Enhanced state detection based on debug output patterns
        lower_text = text.lower()
        
        # Check for precise mode indicators from Claude Code UI
        if "⏵⏵ auto-accept edits on" in text:
            self.mode = "auto-accept"
        elif "⏸ plan mode on" in text:
            self.mode = "plan"
        elif "? for shortcuts" in text:
            self.mode = "interactive"
        elif "Press Ctrl-C again to exit" in text:
            self.mode = "exit-confirm"
        elif "Welcome to Claude Code" in text:
            self.mode = "startup"
        
        # Check for confirmation prompts
        elif any(phrase in lower_text for phrase in ["(y/n)", "yes/no", "confirm", "continue?"]):
            self.mode = "confirmation"
        
        # Check for choice prompts
        elif any(phrase in lower_text for phrase in ["1.", "2.", "3.", "select", "choose"]):
            self.mode = "choice"
        
        # Check for generic error/thinking states  
        elif "thinking" in lower_text or "processing" in lower_text:
            self.mode = "thinking"
        elif "error" in lower_text or "failed" in lower_text:
            self.mode = "error"
        
        # Check for model changes
        elif "Set model to opus" in text:
            self.model = "opus"
        elif "Set model to Default" in text or "Set model to sonnet" in text:
            self.model = "sonnet"
        
        # Check for input prompts (fallback for interactive mode)
        elif ">" in text and not "⏵⏵" in text:  # Exclude auto-accept indicator
            self.mode = "interactive"
        
        # Extract prompt from last line (clean version without escape codes)
        import re
        clean_buffer = re.sub(r'\x1b\[[0-9;]*[mK]', '', self.buffer)  # Remove ANSI codes
        lines = clean_buffer.split('\n')
        for line in reversed(lines):
            clean_line = line.strip()
            if clean_line and '>' in clean_line and not clean_line.startswith('['):
                self.current_prompt = clean_line
                break
    
    def get_state(self) -> Dict[str, Any]:
        """Return current state as dictionary."""
        return {
            "mode": self.mode,
            "model": self.model,
            "prompt": self.current_prompt,
            "last_update": self.last_update,
            "buffer_size": len(self.buffer),
            "button_config": self._get_button_config()
        }
    
    def _get_button_config(self) -> Dict[str, Any]:
        """Return button configuration based on current mode."""
        # Default configuration
        default_config = {
            "shift_tab_icon": "default",
            "shift_tab_label": "Normal", 
            "shift_tab_enabled": True,
            "context_hint": ""
        }
        
        # Mode-specific configurations
        mode_configs = {
            "auto-accept": {
                "shift_tab_icon": "auto-accept",
                "shift_tab_label": "Auto", 
                "context_hint": "Auto-accept mode active"
            },
            "plan": {
                "shift_tab_icon": "plan",
                "shift_tab_label": "Plan",
                "context_hint": "Plan mode active"
            },
            "exit-confirm": {
                "shift_tab_icon": "warning",
                "shift_tab_label": "Exit?",
                "context_hint": "Press Ctrl+C again to exit"
            },
            "confirmation": {
                "shift_tab_icon": "confirm", 
                "shift_tab_label": "Confirm",
                "context_hint": "Confirmation required"
            },
            "choice": {
                "shift_tab_icon": "choose",
                "shift_tab_label": "Choose", 
                "context_hint": "Selection required"
            },
            "thinking": {
                "shift_tab_icon": "default", 
                "shift_tab_label": "Normal",
                "shift_tab_enabled": True,
                "context_hint": "Claude is thinking..."
            },
            "error": {
                "shift_tab_icon": "error",
                "shift_tab_label": "Error",
                "context_hint": "Error state"
            },
            "startup": {
                "shift_tab_icon": "startup",
                "shift_tab_label": "Start",
                "context_hint": "Claude Code starting up"
            },
            "interactive": {
                "shift_tab_icon": "interactive",
                "shift_tab_label": "Ready", 
                "context_hint": "Ready for input"
            }
        }
        
        # Merge default with mode-specific config (Python 3.9+ style)
        if self.mode in mode_configs:
            return default_config | mode_configs[self.mode]
        return default_config


class StreamDeckHandler(BaseHTTPRequestHandler):
    """HTTP handler for Stream Deck communication."""
    
    def __init__(self, claude_wrapper, *args, **kwargs):
        self.claude_wrapper = claude_wrapper
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests - return current Claude state."""
        parsed = urlparse(self.path)
        
        if parsed.path == "/state":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            state = self.claude_wrapper.state.get_state()
            self.wfile.write(json.dumps(state).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests - send commands to Claude."""
        parsed = urlparse(self.path)
        
        if parsed.path == "/command":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                command = data.get('command', '')
                
                if command is not None:
                    success = self.claude_wrapper.send_command(command)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {
                        "status": "sent" if success else "failed",
                        "command": command
                    }
                    self.wfile.write(json.dumps(response).encode())
                else:
                    self.send_response(400)
                    self.end_headers()
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


class ClaudeWrapper:
    """Wrapper class that manages PTY and communication."""
    
    def __init__(self, port=8080, debug_file=None, claude_args=None):
        self.master_fd = None
        self.slave_fd = None
        self.claude_pid = None
        self.state = ClaudeState()
        self.port = port
        self.running = False
        self.debug = False
        self.debug_file = debug_file
        self.debug_handle = None
        self.http_server = None
        self.original_settings = None
        self.claude_args = claude_args or []
    
    def log(self, message):
        """Simple logging."""
        # Completely disable logging to avoid terminal interference
        pass
    
    def start_claude(self):
        """Start Claude Code in a PTY."""
        self.log("Starting Claude Code...")
        
        # Open debug file if specified
        if self.debug_file:
            try:
                self.debug_handle = open(self.debug_file, 'w', encoding='utf-8')
                self.debug_handle.write(f"=== Claude Code Debug Log Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                self.debug_handle.flush()
            except Exception as e:
                print(f"Warning: Could not open debug file {self.debug_file}: {e}")
                self.debug_handle = None
        
        self.master_fd, self.slave_fd = pty.openpty()
        
        self.claude_pid = os.fork()
        if self.claude_pid == 0:
            # Child process - run Claude Code
            os.dup2(self.slave_fd, 0)  # stdin
            os.dup2(self.slave_fd, 1)  # stdout
            os.dup2(self.slave_fd, 2)  # stderr
            os.close(self.master_fd)
            os.close(self.slave_fd)
            
            
            # Execute Claude Code with arguments
            try:
                claude_cmd = ['claude'] + self.claude_args
                os.execvp('claude', claude_cmd)
            except FileNotFoundError:
                print("Error: 'claude' command not found. Make sure Claude Code is installed.")
                sys.exit(1)
        else:
            # Parent process
            os.close(self.slave_fd)
            self.running = True
            self.log(f"Claude started with PID {self.claude_pid}")
    
    def send_command(self, command: str) -> bool:
        """Send a command to Claude Code."""
        if self.master_fd and self.running:
            try:
                # Log to debug file
                if self.debug_handle:
                    timestamp = time.strftime('%H:%M:%S.%f')[:-3]
                    self.debug_handle.write(f"\n[{timestamp}] SEND_COMMAND: {repr(command)}\n")
                
                # Check if this is a special escape sequence
                if command.startswith('\x1b'):
                    # For escape sequences, send directly without extra CR
                    data = command.encode()
                    os.write(self.master_fd, data)
                    if self.debug_handle:
                        self.debug_handle.write(f"SENT_RAW: {repr(data)}\n")
                        self.debug_handle.flush()
                    self.log(f"Sent escape sequence: {repr(command)}")
                elif command == "":
                    # For empty command (OK button), just send carriage return
                    data = b'\r'
                    os.write(self.master_fd, data)
                    if self.debug_handle:
                        self.debug_handle.write(f"SENT_RAW: {repr(data)}\n")
                        self.debug_handle.flush()
                    self.log(f"Sent carriage return")
                else:
                    # For regular commands, send command + CR
                    cmd_data = command.encode()
                    os.write(self.master_fd, cmd_data)
                    if self.debug_handle:
                        self.debug_handle.write(f"SENT_RAW: {repr(cmd_data)}\n")
                    
                    # Minimal delay to let command be processed
                    time.sleep(0.001)
                    
                    # Send carriage return to execute (for inquirer.js compatibility)
                    cr_data = b'\r'
                    os.write(self.master_fd, cr_data)
                    if self.debug_handle:
                        self.debug_handle.write(f"SENT_RAW: {repr(cr_data)} (CR)\n")
                        self.debug_handle.flush()
                    
                    self.log(f"Sent command: {repr(command)} + CR")
                
                return True
            except OSError as e:
                self.log(f"Failed to send command: {e}")
                return False
        return False
    
    def start_http_server(self):
        """Start HTTP server for Stream Deck communication."""
        def handler(*args, **kwargs):
            return StreamDeckHandler(self, *args, **kwargs)
        
        try:
            self.http_server = HTTPServer(('localhost', self.port), handler)
            # Enable socket reuse to prevent "Address already in use" errors
            self.http_server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.log(f"HTTP server listening on http://localhost:{self.port}")
            self.http_server.serve_forever()
        except OSError as e:
            self.log(f"Failed to start HTTP server on port {self.port}: {e}")
    
    def setup_terminal(self):
        """Setup terminal for raw mode to forward all keystrokes."""
        try:
            # Save original terminal settings
            self.original_settings = termios.tcgetattr(sys.stdin)
            
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
            
            # Handle window size changes
            def handle_winch(signum, frame):
                # Get terminal size and forward to PTY
                try:
                    s = struct.pack("HHHH", 0, 0, 0, 0)
                    size = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s)
                    fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
                except OSError:
                    pass
            
            signal.signal(signal.SIGWINCH, handle_winch)
            
            # Set initial window size
            try:
                s = struct.pack("HHHH", 0, 0, 0, 0)
                size = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
            except OSError:
                pass
                
        except termios.error as e:
            self.log(f"Warning: Could not set terminal to raw mode: {e}")

    def run(self):
        """Main run loop - handles terminal I/O."""
        self.start_claude()
        
        # Setup terminal for raw input forwarding
        self.setup_terminal()
        
        # Give Claude a moment to start
        time.sleep(0.5)
        
        # Start HTTP server in background thread
        http_thread = threading.Thread(target=self.start_http_server, daemon=True)
        http_thread.start()
        
        self.log("Starting I/O loop...")
        
        try:
            while self.running:
                # Monitor both master_fd for Claude output and stdin for user input
                ready, _, _ = select.select([self.master_fd, sys.stdin], [], [], 0.1)
                
                if self.master_fd in ready:
                    try:
                        data = os.read(self.master_fd, 1024)
                        if data:
                            # Write to debug file if enabled
                            if self.debug_handle:
                                try:
                                    # Write timestamp and raw data
                                    timestamp = time.strftime('%H:%M:%S.%f')[:-3]  # milliseconds
                                    self.debug_handle.write(f"\n[{timestamp}] OUT ({len(data)} bytes):\n")
                                    # Write both raw repr and decoded text
                                    self.debug_handle.write(f"RAW: {repr(data)}\n")
                                    try:
                                        text = data.decode('utf-8', errors='replace')
                                        self.debug_handle.write(f"TEXT: {repr(text)}\n")
                                        # Also write cleaned version for readability
                                        clean_text = text.replace('\r\n', '\\r\\n').replace('\n', '\\n').replace('\r', '\\r')
                                        self.debug_handle.write(f"CLEAN: {clean_text}\n")
                                    except:
                                        self.debug_handle.write("TEXT: <decode error>\n")
                                    self.debug_handle.flush()
                                except Exception as e:
                                    print(f"Debug write error: {e}")
                            
                            # Parse state and forward to stdout
                            self.state.parse_output(data)
                            # Forward Claude's output to terminal
                            sys.stdout.buffer.write(data)
                            sys.stdout.buffer.flush()
                        else:
                            # Claude exited
                            self.log("Claude exited")
                            break
                    except OSError as e:
                        self.log(f"Error reading from Claude: {e}")
                        break
                
                if sys.stdin in ready:
                    # User input -> forward to Claude
                    try:
                        data = os.read(sys.stdin.fileno(), 1024)
                        if data:
                            # Write to debug file if enabled
                            if self.debug_handle:
                                try:
                                    timestamp = time.strftime('%H:%M:%S.%f')[:-3]
                                    self.debug_handle.write(f"\n[{timestamp}] IN ({len(data)} bytes):\n")
                                    self.debug_handle.write(f"RAW: {repr(data)}\n")
                                    try:
                                        text = data.decode('utf-8', errors='replace')
                                        self.debug_handle.write(f"TEXT: {repr(text)}\n")
                                    except:
                                        self.debug_handle.write("TEXT: <decode error>\n")
                                    self.debug_handle.flush()
                                except Exception as e:
                                    print(f"Debug write error: {e}")
                            
                            os.write(self.master_fd, data)
                    except OSError as e:
                        self.log(f"Error forwarding user input: {e}")
                        break
                
                # Check if Claude process is still alive
                try:
                    pid, status = os.waitpid(self.claude_pid, os.WNOHANG)
                    if pid == self.claude_pid:
                        self.log(f"Claude process exited with status {status}")
                        break
                except OSError:
                    pass
        
        except KeyboardInterrupt:
            self.log("Received interrupt signal")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        self.log("Cleaning up...")
        self.running = False
        
        # Close debug file
        if self.debug_handle:
            try:
                self.debug_handle.write(f"\n=== Claude Code Debug Log Ended at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                self.debug_handle.close()
            except Exception as e:
                print(f"Error closing debug file: {e}")
        
        # Restore terminal settings
        if self.original_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
            except termios.error:
                pass
        
        # Close HTTP server
        if self.http_server:
            self.log("Shutting down HTTP server...")
            self.http_server.shutdown()
            self.http_server.server_close()
        
        if self.master_fd:
            os.close(self.master_fd)
        if self.claude_pid:
            try:
                os.kill(self.claude_pid, 15)  # SIGTERM
                time.sleep(0.5)
                # Force kill if still running
                try:
                    os.kill(self.claude_pid, 9)  # SIGKILL
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Claude Code + Stream Deck PTY Wrapper')
    parser.add_argument('--port', type=int, default=8080, 
                       help='HTTP server port for Stream Deck API (default: 8080)')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress debug output')
    parser.add_argument('--debug-file', type=str, 
                       help='File to write debug terminal output to (enables detailed logging)')
    parser.add_argument('claude_args', nargs='*', 
                       help='Arguments to pass to Claude Code (e.g., --continue, --resume)')
    
    args = parser.parse_args()
    
    print("Claude Code + Stream Deck Wrapper")
    print("=" * 50)
    
    if args.debug_file:
        print(f"Debug mode enabled - writing terminal output to: {args.debug_file}")
    
    if args.claude_args:
        print(f"Claude args: {' '.join(args.claude_args)}")
    
    wrapper = ClaudeWrapper(port=args.port, debug_file=args.debug_file, claude_args=args.claude_args)
    wrapper.debug = not args.quiet
    wrapper.run()


if __name__ == '__main__':
    main()