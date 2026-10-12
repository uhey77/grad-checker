import type { AuthSession, AuthPolicy } from "../domain/models.ts";

export class AuthError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
  }
}
export interface AuthRepository {
  config(signal?: AbortSignal): Promise<AuthPolicy>;
  session(signal?: AbortSignal): Promise<AuthSession | null>;
  register(email: string, signal?: AbortSignal): Promise<void>;
  verify(token: string, password: string, signal?: AbortSignal): Promise<void>;
  login(
    email: string,
    password: string,
    signal?: AbortSignal,
  ): Promise<AuthSession>;
  logout(csrf: string, signal?: AbortSignal): Promise<void>;
}
export class AuthUseCases implements AuthRepository {
  constructor(private readonly repository: AuthRepository) {}
  config(signal?: AbortSignal) {
    return this.repository.config(signal);
  }
  session(signal?: AbortSignal) {
    return this.repository.session(signal);
  }
  register(email: string, signal?: AbortSignal) {
    return this.repository.register(email, signal);
  }
  verify(token: string, password: string, signal?: AbortSignal) {
    return this.repository.verify(token, password, signal);
  }
  login(email: string, password: string, signal?: AbortSignal) {
    return this.repository.login(email, password, signal);
  }
  logout(csrf: string, signal?: AbortSignal) {
    return this.repository.logout(csrf, signal);
  }
}
