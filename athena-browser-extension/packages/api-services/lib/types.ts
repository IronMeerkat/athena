export type Unsubscribe = () => void;

export type SsoEventType =
  | { type: 'sso:login'; payload: { userId: string } }
  | { type: 'sso:logout' }
  | { type: 'sso:token'; payload: { accessToken: string; refreshToken?: string | null } };

export type LoginCredentials = { username: string; password: string };

export type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  isAuthenticated: boolean;
};

export type LoginResult = { ok: true } | { ok: false; message?: string };

export type WebSocketMessage = { type: string; [key: string]: unknown };

