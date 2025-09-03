export class AuthRequiredError extends Error {
  readonly status: number | null;
  constructor(message = 'Authentication required', status: number | null = 401) {
    super(message);
    this.name = 'AuthRequiredError';
    this.status = status;
  }
}

export const isAuthRequiredError = (error: unknown): error is AuthRequiredError => {
  return error instanceof AuthRequiredError;
};

