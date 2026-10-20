import type { AuthSession } from "../dto/auth.ts";
import type { AuthPolicy } from "../../domain/value_objects/authPolicy.ts";
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
