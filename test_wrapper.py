#!/usr/bin/env python3
"""
Test script for the Claude Wrapper API
"""

import requests
import json
import time

def test_api(port=8080):
    """Test the wrapper API endpoints."""
    base_url = f"http://localhost:{port}"
    
    print("Testing Claude Wrapper API")
    print("=" * 30)
    
    # Test getting state
    try:
        response = requests.get(f"{base_url}/state", timeout=5)
        if response.status_code == 200:
            state = response.json()
            print(f"✓ Current state: {json.dumps(state, indent=2)}")
        else:
            print(f"✗ State request failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to wrapper API: {e}")
        print("Make sure the wrapper is running!")
        return
    
    # Test sending a command
    test_command = "help"
    try:
        response = requests.post(
            f"{base_url}/command",
            json={"command": test_command},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Command '{test_command}' sent: {result}")
        else:
            print(f"✗ Command request failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Command request failed: {e}")
    
    # Wait and check state again
    print("\nWaiting 2 seconds, then checking state again...")
    time.sleep(2)
    
    try:
        response = requests.get(f"{base_url}/state", timeout=5)
        if response.status_code == 200:
            state = response.json()
            print(f"✓ Updated state: {json.dumps(state, indent=2)}")
        else:
            print(f"✗ State request failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ State request failed: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Claude Wrapper API')
    parser.add_argument('--port', type=int, default=8080,
                       help='Wrapper API port (default: 8080)')
    
    args = parser.parse_args()
    test_api(args.port)