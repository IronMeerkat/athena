export type LoginCredentials = { username: string; password: string };

export type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  isAuthenticated: boolean;
};

export type LoginResult = { ok: true } | { ok: false; message?: string };


