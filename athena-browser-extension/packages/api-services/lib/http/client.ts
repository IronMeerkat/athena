import axios from 'axios';
import { AuthRequiredError } from './errors.js';
import { authStore } from '../auth/store.js';

type CreateClientOptions = {
  baseURL: string;
  getToken?: () => string | null;
};

export const createHttpClient = (options: CreateClientOptions) => {
  const instance = axios.create({
    baseURL: options.baseURL,
    withCredentials: true,
  });

  instance.interceptors.request.use(config => {
    const explicit = options.getToken?.();
    const token = explicit ?? authStore.getState().accessToken;
    if (token) {
      config.headers = config.headers ?? {};
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    config.headers = config.headers ?? {};
    config.headers['Accept'] = 'application/json';
    return config;
  });

  instance.interceptors.response.use(
    r => r,
    error => {
      const status: number | undefined = error?.response?.status;
      if (status === 401 || status === 403) {
        // Ensure we never swallow the error silently
        console.error('Auth error from API:', status, error?.response?.data);
        throw new AuthRequiredError('Please log in to continue', status);
      }
      // Ensure logging for unexpected errors
      console.error('HTTP error:', error?.message || error);
      return Promise.reject(error);
    },
  );

  return instance;
};

