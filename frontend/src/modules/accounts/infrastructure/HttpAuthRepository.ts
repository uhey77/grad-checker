import { createDtoReader } from "../../../shared/infrastructure/dtoReader.ts";
import {
  requestJson,
  type JsonRequest,
} from "../../../shared/infrastructure/http.ts";
import { AuthError } from "../application/errors/AuthError.ts";
import { type AuthRepository } from "../application/ports/AuthRepository.ts";
import type { AuthSession, AuthPolicy } from "../domain/models.ts";

const recoveryCodePattern = /^[A-Za-z0-9_-]{43}$/;

function reader(message: string) {
  return createDtoReader(() => {
    throw new AuthError(502, message);
  });
}
const sessionReader = reader("認証情報を読み込めません。");
const policyReader = reader("認証設定を読み込めません。");
const recoveryReader = reader("登録・復旧の結果を読み込めません。");
const logoutReader = reader("ログアウト結果を読み込めません。");

function toSession(data: unknown): AuthSession {
  const { record, text, invalid } = sessionReader;
  const value = record(data);
  const student = record(value.student);
  const expiresAt = text(value.expires_at);
  if (value.authenticated !== true || !Number.isFinite(Date.parse(expiresAt)))
    return invalid();
  return {
    student: { id: text(student.id), loginName: text(student.login_name) },
    csrfToken: text(value.csrf_token),
    expiresAt,
  };
}

export class HttpAuthRepository implements AuthRepository {
  constructor(private readonly base: string) {}
  private request(path: string, request: JsonRequest): Promise<unknown> {
    return requestJson(
      this.base + path,
      request,
      (status, message) => new AuthError(status, message),
      {
        unreadable: "サーバーの応答を読み込めません。再試行してください。",
        unreadableFailure:
          "認証処理に失敗しました。時間をおいて再試行してください。",
        failed: "認証処理に失敗しました。",
      },
    );
  }
  async config(signal?: AbortSignal): Promise<AuthPolicy> {
    const { record, integer, invalid } = policyReader;
    const policy = record(
      record(await this.request("/config", { signal })).policy,
    );
    const passwordMinLength = integer(policy.password_min_length, 1);
    const passwordMaxLength = integer(policy.password_max_length, 1);
    if (passwordMinLength > passwordMaxLength) return invalid();
    return { passwordMinLength, passwordMaxLength };
  }
  async session(signal?: AbortSignal) {
    try {
      return toSession(await this.request("/session", { signal }));
    } catch (error) {
      if (error instanceof AuthError && error.status === 401) return null;
      throw error;
    }
  }
  private recoveryResult(
    data: unknown,
    field: "registered" | "recovered",
  ): string {
    const { record, text, invalid } = recoveryReader;
    const result = record(data);
    const code = text(result.recovery_code);
    if (result[field] !== true || !recoveryCodePattern.test(code))
      return invalid();
    return code;
  }
  async register(loginName: string, password: string, signal?: AbortSignal) {
    return this.recoveryResult(
      await this.request("/register", {
        method: "POST",
        payload: { login_name: loginName, password },
        signal,
      }),
      "registered",
    );
  }
  async recover(
    loginName: string,
    recoveryCode: string,
    password: string,
    signal?: AbortSignal,
  ) {
    return this.recoveryResult(
      await this.request("/recover", {
        method: "POST",
        payload: {
          login_name: loginName,
          recovery_code: recoveryCode,
          password,
        },
        signal,
      }),
      "recovered",
    );
  }
  async login(loginName: string, password: string, signal?: AbortSignal) {
    return toSession(
      await this.request("/login", {
        method: "POST",
        payload: { login_name: loginName, password },
        signal,
      }),
    );
  }
  async logout(csrf: string, signal?: AbortSignal) {
    const { record, invalid } = logoutReader;
    const data = record(
      await this.request("/logout", {
        method: "POST",
        payload: {},
        csrf,
        signal,
      }),
    );
    if (data.authenticated !== false) invalid();
  }
}
