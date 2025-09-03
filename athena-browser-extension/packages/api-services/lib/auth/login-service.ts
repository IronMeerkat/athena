import { createHttpClient } from '../http/client.js';
import type { LoginCredentials, LoginResult } from '../types.js';
import { authStore } from './store.js';
import { ssoEvents } from '../sso/events.js';

export type LoginServiceOptions = {
  baseURL: string;
  endpoints?: {
    login: string; // e.g. '/api/auth/login/' for DRF
    me?: string; // e.g. '/api/auth/me/'
    refresh?: string; // e.g. '/api/auth/refresh/'
    logout?: string; // e.g. '/api/auth/logout/'
  };
};

export const createLoginService = (options: LoginServiceOptions) => {
  const http = createHttpClient({ baseURL: options.baseURL });
  const endpoints = {
    login: '/api/auth/login/',
    me: '/api/auth/me/',
    refresh: '/api/auth/refresh/',
    logout: '/api/auth/logout/',
    ...(options.endpoints ?? {}),
  };

  const loginWithCredentials = async (credentials: LoginCredentials): Promise<LoginResult> => {
    try {
      const res = await http.post(endpoints.login, credentials);
      const { access, refresh, user } = res.data as {
        access?: string;
        refresh?: string | null;
        user?: { id?: string | number } | null;
      };
      await authStore.getState().setTokens(access ?? null, refresh ?? null);
      await authStore.getState().setUser(user?.id != null ? String(user.id) : null);
      ssoEvents.post({ type: 'sso:login', payload: { userId: authStore.getState().userId! } });
      if (access) ssoEvents.post({ type: 'sso:token', payload: { accessToken: access, refreshToken: refresh ?? null } });
      return { ok: true } as const;
    } catch (e) {
      console.error('Login failed', e);
      return { ok: false, message: 'Invalid credentials or server error' } as const;
    }
  };

  const refreshToken = async (): Promise<boolean> => {
    const refresh = authStore.getState().refreshToken;
    if (!refresh) return false;
    try {
      const res = await http.post(endpoints.refresh, { refresh });
      const { access } = res.data as { access?: string };
      await authStore.getState().setTokens(access ?? null, refresh);
      if (access) ssoEvents.post({ type: 'sso:token', payload: { accessToken: access, refreshToken: refresh } });
      return Boolean(access);
    } catch (e) {
      console.error('Refresh failed', e);
      return false;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await http.post(endpoints.logout);
    } catch (e) {
      console.error('Logout request failed', e);
    }
    await authStore.getState().clear();
    ssoEvents.post({ type: 'sso:logout' });
  };

  const fetchMe = async (): Promise<{ id: string } | null> => {
    try {
      const res = await http.get(endpoints.me);
      const user = res.data as { id?: string | number };
      const id = user?.id != null ? String(user.id) : null;
      await authStore.getState().setUser(id);
      return id ? { id } : null;
    } catch (e) {
      console.error('Fetch me failed', e);
      return null;
    }
  };

  return { loginWithCredentials, refreshToken, logout, fetchMe };
};

