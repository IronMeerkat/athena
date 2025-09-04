import { create } from '../vendor/zustand.js';
import type { AuthState } from '@extension/types';

type Store = AuthState & {
  setTokens: (accessToken: string | null, refreshToken?: string | null) => Promise<void>;
  setUser: (userId: string | null) => Promise<void>;
  clear: () => Promise<void>;
};

const storageKey = 'athena:auth';

const readStorage = async (): Promise<Partial<AuthState>> => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const c = (globalThis as any).chrome as { storage?: { local?: { get?: (keys: string[]) => Promise<Record<string, unknown>> } } } | undefined;
  try {
    const v = await c?.storage?.local?.get?.([storageKey]);
    const raw = v?.[storageKey];
    if (raw && typeof raw === 'object') {
      return raw as Partial<AuthState>;
    }
  } catch (e) {
    console.error('Auth store load error', e);
  }
  return {};
};

const writeStorage = async (state: AuthState): Promise<void> => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const c = (globalThis as any).chrome as { storage?: { local?: { set?: (items: Record<string, unknown>) => Promise<void> } } } | undefined;
  try {
    await c?.storage?.local?.set?.({ [storageKey]: state });
  } catch (e) {
    console.error('Auth store save error', e);
  }
};

export const authStore = create<Store>((set, get) => {
  const initial: Store = {
    accessToken: null,
    refreshToken: null,
    userId: null,
    isAuthenticated: false,
    async setTokens(accessToken, refreshToken = null) {
      const next = {
        ...get(),
        accessToken,
        refreshToken,
        isAuthenticated: Boolean(accessToken),
      } as Store;
      set(next);
      await writeStorage(next);
    },
    async setUser(userId) {
      const next = { ...get(), userId } as Store;
      set(next);
      await writeStorage(next);
    },
    async clear() {
      const next = {
        accessToken: null,
        refreshToken: null,
        userId: null,
        isAuthenticated: false,
      } as Store;
      set(next);
      await writeStorage(next);
    },
  };

  // Initialize from storage synchronously-ish
  void readStorage().then(saved => {
    const next = {
      ...initial,
      ...saved,
      isAuthenticated: Boolean(saved.accessToken ?? initial.accessToken),
    } as Store;
    set(next);
  });

  return initial;
});

