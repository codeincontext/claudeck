#!/usr/bin/env python3
"""
Simplified Claude Code + Stream Deck PTY Wrapper

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
        self.current_prompt = ""
        self.buffer = ""
        self.last_update = time.time()
    
    def parse_output(self, data: bytes) -> None:
        """Parse terminal output to extract current state."""
        text = data.decode('utf-8', errors='ignore')
        self.buffer += text
        self.last_update = time.time()
        
        # Keep only last 1000 chars to prevent memory bloat
        if len(self.buffer) > 1000:
            self.buffer = self.buffer[-1000:]
        
        # Simple state detection
        lower_text = text.lower()
        if "planning mode" in lower_text or "/plan" in lower_text:
            self.mode = "planning"
        elif "auto-accept" in lower_text or "/auto" in lower_text:
            self.mode = "auto-accept"
        elif "welcome to claude code" in lower_text:
            self.mode = "interactive"
        elif ">" in text:
            self.mode = "interactive"
        
        # Extract prompt from last line
        lines = self.buffer.split('\n')
        for line in reversed(lines):
            clean_line = line.strip()
            if clean_line and '>' in clean_line:
                self.current_prompt = clean_line
                break
    
    def get_state(self) -> Dict[str, Any]:
        """Return current state as dictionary."""
        return {
            "mode": self.mode,
            "prompt": self.current_prompt,
            "last_update": self.last_update,
            "buffer_size": len(self.buffer)
        }


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
                
                if command:
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
    """Simplified wrapper class that manages PTY and communication."""
    
    def __init__(self, port=8080):
        self.master_fd = None
        self.slave_fd = None
        self.claude_pid = None
        self.state = ClaudeState()
        self.port = port
        self.running = False
        self.debug = True
        self.http_server = None
        self.original_settings = None
    
    def log(self, message):
        """Simple logging."""
        if self.debug:
            print(f"[WRAPPER] {message}")
    
    def start_claude(self):
        """Start Claude Code in a PTY."""
        self.log("Starting Claude Code...")
        self.master_fd, self.slave_fd = pty.openpty()
        
        self.claude_pid = os.fork()
        if self.claude_pid == 0:
            # Child process - run Claude Code
            os.dup2(self.slave_fd, 0)  # stdin
            os.dup2(self.slave_fd, 1)  # stdout
            os.dup2(self.slave_fd, 2)  # stderr
            os.close(self.master_fd)
            os.close(self.slave_fd)
            
            
            # Execute Claude Code
            try:
                os.execvp('claude', ['claude'])
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
                # Send command first
                os.write(self.master_fd, command.encode())
                
                # Minimal delay to let command be processed
                time.sleep(0.001)
                
                # Send carriage return to execute (for inquirer.js compatibility)
                os.write(self.master_fd, b'\r')
                
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
    
    parser = argparse.ArgumentParser(description='Simplified Claude Code + Stream Deck PTY Wrapper')
    parser.add_argument('--port', type=int, default=8080, 
                       help='HTTP server port for Stream Deck API (default: 8080)')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress debug output')
    
    args = parser.parse_args()
    
    print("Claude Code + Stream Deck Wrapper (Simplified)")
    print("=" * 50)
    
    wrapper = ClaudeWrapper(port=args.port)
    wrapper.debug = not args.quiet
    wrapper.run()


if __name__ == '__main__':
    main()