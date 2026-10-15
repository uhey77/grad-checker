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
  register(
    loginName: string,
    password: string,
    signal?: AbortSignal,
  ): Promise<string>;
  recover(
    loginName: string,
    recoveryCode: string,
    password: string,
    signal?: AbortSignal,
  ): Promise<string>;
  login(
    loginName: string,
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
  register(loginName: string, password: string, signal?: AbortSignal) {
    return this.repository.register(loginName, password, signal);
  }
  recover(
    loginName: string,
    recoveryCode: string,
    password: string,
    signal?: AbortSignal,
  ) {
    return this.repository.recover(loginName, recoveryCode, password, signal);
  }
  login(loginName: string, password: string, signal?: AbortSignal) {
    return this.repository.login(loginName, password, signal);
  }
  logout(csrf: string, signal?: AbortSignal) {
    return this.repository.logout(csrf, signal);
  }
}
