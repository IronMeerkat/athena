export type SsoEventType =
  | { type: 'sso:login'; payload: { userId: string } }
  | { type: 'sso:logout' }
  | { type: 'sso:token'; payload: { accessToken: string; refreshToken?: string | null } };


