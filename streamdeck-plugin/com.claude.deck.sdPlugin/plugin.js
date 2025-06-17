/// <reference path="libs/js/stream-deck.js" />

// Global websocket connection
let websocket = null;

// Connect to Stream Deck
function connectElgatoStreamDeckSocket(inPort, inPluginUUID, inRegisterEvent, inInfo) {
    websocket = new WebSocket('ws://localhost:' + inPort);
    
    websocket.onopen = function () {
        // Register plugin
        const json = {
            event: inRegisterEvent,
            uuid: inPluginUUID
        };
        websocket.send(JSON.stringify(json));
    };

    websocket.onmessage = function (evt) {
        const jsonObj = JSON.parse(evt.data);
        const event = jsonObj.event;
        const context = jsonObj.context;
        
        if (event === 'keyDown') {
            handleKeyDown(context, jsonObj.payload);
        }
    };
}

// Handle button press
function handleKeyDown(context, payload) {
    const settings = payload.settings || {};
    const command = settings.command || 'help';
    
    // Send command to Claude wrapper
    sendClaudeCommand(command)
        .then(() => {
            // Show success feedback
            showOk(context);
        })
        .catch(error => {
            console.error('Failed to send command:', error);
            showAlert(context);
        });
}

// Send command to Claude wrapper via HTTP
async function sendClaudeCommand(command) {
    const wrapperUrl = 'http://localhost:8080';
    
    const response = await fetch(`${wrapperUrl}/command`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ command: command })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
}

// Show success feedback
function showOk(context) {
    const json = {
        event: 'showOk',
        context: context
    };
    websocket.send(JSON.stringify(json));
}

// Show error feedback
function showAlert(context) {
    const json = {
        event: 'showAlert',
        context: context
    };
    websocket.send(JSON.stringify(json));
}

// Property Inspector handling
function sendToPropertyInspector(context, payload) {
    const json = {
        event: 'sendToPropertyInspector',
        context: context,
        payload: payload
    };
    websocket.send(JSON.stringify(json));
}

// Update title with Claude state
async function updateButtonTitle(context) {
    try {
        const response = await fetch('http://localhost:8080/state');
        const state = await response.json();
        
        const json = {
            event: 'setTitle',
            context: context,
            payload: {
                title: state.mode || 'Claude',
                target: 0  // hardware and software
            }
        };
        websocket.send(JSON.stringify(json));
    } catch (error) {
        console.error('Failed to get Claude state:', error);
    }
}

// Periodic state updates
setInterval(() => {
    // This would need context tracking to work properly
    // For now, just log state updates
    fetch('http://localhost:8080/state')
        .then(response => response.json())
        .then(state => {
            console.log('Claude state:', state);
        })
        .catch(error => {
            console.error('State check failed:', error);
        });
}, 5000);