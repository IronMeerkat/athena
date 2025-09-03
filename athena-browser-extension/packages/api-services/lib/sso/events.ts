import { SSO_BROADCAST_CHANNEL } from './const.js';
import type { SsoEventType, Unsubscribe } from '../types.js';

type Listener = (event: SsoEventType) => void;

class SsoEventHub {
  private listeners: Set<Listener> = new Set();
  private channel: BroadcastChannel | null = null;

  constructor() {
    try {
      this.channel = new BroadcastChannel(SSO_BROADCAST_CHANNEL);
      this.channel.onmessage = e => this.emit(e.data as SsoEventType);
    } catch (e) {
      // Fallback to chrome.runtime message passing
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const c = (globalThis as any).chrome as { runtime?: { onMessage?: { addListener?: (cb: (message: unknown) => void) => void }, sendMessage?: (msg: unknown) => void } } | undefined;
        c?.runtime?.onMessage?.addListener?.((message: unknown) => {
          if (typeof message === 'object' && message && 'type' in (message as Record<string, unknown>)) {
            const type = (message as { type: string }).type;
            if (type?.startsWith('sso:')) {
              this.emit(message as SsoEventType);
            }
          }
        });
      } catch {
        // no-op
      }
    }
  }

  on(listener: Listener): Unsubscribe {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  emit(event: SsoEventType): void {
    for (const l of this.listeners) {
      try {
        l(event);
      } catch (err) {
        console.error('SSO listener error', err);
      }
    }
  }

  post(event: SsoEventType): void {
    try {
      if (this.channel) {
        this.channel.postMessage(event);
      } else {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const c = (globalThis as any).chrome as { runtime?: { sendMessage?: (msg: unknown) => void } } | undefined;
        c?.runtime?.sendMessage?.(event);
      }
    } catch (err) {
      console.error('SSO post error', err);
    }
    this.emit(event);
  }
}

export const ssoEvents = new SsoEventHub();

