import type { Event } from "@/lib/types";

export type WSState = "connecting" | "connected" | "disconnected" | "error";

export type EventCallback = (event: Event) => void;
export type StateCallback = (state: WSState) => void;

const WS_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000")
    : "ws://localhost:8000";

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private runId: string;
  private onEvent: EventCallback;
  private onStateChange: StateCallback;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 8;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;

  constructor(
    runId: string,
    onEvent: EventCallback,
    onStateChange: StateCallback
  ) {
    this.runId = runId;
    this.onEvent = onEvent;
    this.onStateChange = onStateChange;
  }

  connect() {
    if (this.closed) return;
    this.onStateChange("connecting");

    const url = `${WS_BASE}/ws/runs/${this.runId}/debate`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.onStateChange("connected");
    };

    this.ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        // Backend may send array (replay) or single event
        if (Array.isArray(data)) {
          data.forEach((ev: Event) => this.onEvent(ev));
        } else {
          this.onEvent(data as Event);
        }
      } catch {
        // silently ignore malformed WS messages
      }
    };

    this.ws.onerror = () => {
      this.onStateChange("error");
    };

    this.ws.onclose = () => {
      if (!this.closed) {
        this.scheduleReconnect();
      } else {
        this.onStateChange("disconnected");
      }
    };
  }

  private scheduleReconnect() {
    if (this.closed || this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.onStateChange("disconnected");
      return;
    }
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  disconnect() {
    this.closed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.onStateChange("disconnected");
  }
}
