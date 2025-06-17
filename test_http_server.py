#!/usr/bin/env python3
"""
Test HTTP server functionality separately
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class TestState:
    def __init__(self):
        self.mode = "test"
        self.prompt = "test> "
        self.commands_received = []
    
    def get_state(self):
        return {
            "mode": self.mode,
            "prompt": self.prompt,
            "commands_received": self.commands_received
        }


class TestHandler(BaseHTTPRequestHandler):
    def __init__(self, state, *args, **kwargs):
        self.state = state
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/state":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            state = self.state.get_state()
            self.wfile.write(json.dumps(state).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/command":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                command = data.get('command', '')
                
                print(f"Received command: {command}")
                self.state.commands_received.append(command)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "received", "command": command}).encode())
                
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress default HTTP logging


def main():
    state = TestState()
    port = 8080
    
    def handler(*args, **kwargs):
        return TestHandler(state, *args, **kwargs)
    
    try:
        server = HTTPServer(('localhost', port), handler)
        print(f"Test HTTP server listening on http://localhost:{port}")
        print("Test endpoints:")
        print("  GET  /state   - Get test state")
        print("  POST /command - Receive test command")
        print("Press Ctrl+C to stop")
        server.serve_forever()
    except OSError as e:
        print(f"Failed to start server on port {port}: {e}")
    except KeyboardInterrupt:
        print("\nStopping server...")


if __name__ == '__main__':
    main()