import { useEffect } from 'react';
import type { RuntimeMessage } from '../types/messages';

export function useRuntimeMessage(handler: (message: RuntimeMessage) => void): void {
  useEffect(() => {
    const listener = (message: unknown) => {
      if (
        typeof message === 'object' &&
        message !== null &&
        'type' in message &&
        typeof (message as { type?: unknown }).type === 'string'
      ) {
        handler(message as RuntimeMessage);
      }
    };
    // The Chrome typings might not be available in this context, cast narrowly
    const api = chrome?.runtime?.onMessage as
      | { addListener: (cb: (msg: unknown) => void) => void; removeListener: (cb: (msg: unknown) => void) => void }
      | undefined;
    api?.addListener(listener);
    return () => {
      api?.removeListener(listener);
    };
  }, [handler]);
}
