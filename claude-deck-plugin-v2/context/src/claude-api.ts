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