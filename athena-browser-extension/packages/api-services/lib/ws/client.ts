import type { WebSocketMessage } from '../types.js';
import { AuthRequiredError } from '../http/errors.js';
import { authStore } from '../auth/store.js';

export type WebSocketClientOptions = {
  url: string; // base ws(s) url, e.g. wss://example.com/ws/stream/
  protocols?: string | string[];
  autoReconnect?: boolean;
};

export class WebSocketClient {
  private options: Required<WebSocketClientOptions>;
  private ws: WebSocket | null = null;
  private listeners: Set<(msg: MessageEvent) => void> = new Set();
  private closedByUser = false;
  private retryDelayMs = 1000;

  constructor(opts: WebSocketClientOptions) {
    this.options = {
      autoReconnect: true,
      protocols: [],
      ...opts,
    } as Required<WebSocketClientOptions>;
  }

  connect(): void {
    const token = authStore.getState().accessToken;
    const url = new URL(this.options.url);
    if (token) url.searchParams.set('token', token);
    try {
      this.ws = new WebSocket(url.toString(), this.options.protocols);
    } catch (e) {
      console.error('WebSocket connect error', e);
      if (this.options.autoReconnect) this.scheduleReconnect();
      return;
    }
    this.closedByUser = false;

    this.ws.onopen = () => {
      this.retryDelayMs = 1000;
    };
    this.ws.onclose = () => {
      if (!this.closedByUser && this.options.autoReconnect) this.scheduleReconnect();
    };
    this.ws.onerror = err => {
      console.error('WebSocket error', err);
    };
    this.ws.onmessage = ev => {
      if (typeof ev.data === 'string') {
        try {
          const msg = JSON.parse(ev.data) as WebSocketMessage;
          if (msg.type === 'unauthorized') {
            console.error('WebSocket unauthorized message');
            this.listeners.forEach(l => l(ev));
            throw new AuthRequiredError('WebSocket unauthorized', 401);
          }
        } catch (e) {
          // fall through to listener anyway
        }
      }
      this.listeners.forEach(l => l(ev));
    };
  }

  private scheduleReconnect(): void {
    const delay = Math.min(1000 * 60, this.retryDelayMs);
    setTimeout(() => this.connect(), delay);
    this.retryDelayMs = Math.min(1000 * 60, Math.round(this.retryDelayMs * 1.6));
  }

  send(data: unknown): void {
    try {
      this.ws?.send(typeof data === 'string' ? data : JSON.stringify(data));
    } catch (e) {
      console.error('WebSocket send error', e);
    }
  }

  on(listener: (msg: MessageEvent) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  close(): void {
    this.closedByUser = true;
    try {
      this.ws?.close();
    } catch (e) {
      console.error('WebSocket close error', e);
    }
  }
}

