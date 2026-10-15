import { AuthError, type AuthRepository } from "../application/AuthUseCases.ts";
import type { AuthSession, AuthPolicy } from "../domain/models.ts";

function toSession(data: unknown): AuthSession {
  if (!data || typeof data !== "object")
    throw new AuthError(502, "認証情報を読み込めません。");
  const value = data as Record<string, unknown>;
  const student = value.student as Record<string, unknown> | undefined;
  if (
    value.authenticated !== true ||
    !student ||
    typeof student.id !== "string" ||
    typeof student.login_name !== "string" ||
    typeof value.csrf_token !== "string" ||
    typeof value.expires_at !== "string" ||
    !Number.isFinite(Date.parse(value.expires_at))
  )
    throw new AuthError(502, "認証情報を読み込めません。");
  return {
    student: { id: student.id, email: student.login_name },
    csrfToken: value.csrf_token,
    expiresAt: value.expires_at,
  };
}
export class HttpAuthRepository implements AuthRepository {
  constructor(private readonly base: string) {}
  private async request(
    path: string,
    payload?: object,
    signal?: AbortSignal,
    csrf?: string,
  ): Promise<unknown> {
    try {
      const response = await fetch(this.base + path, {
        method: payload ? "POST" : "GET",
        credentials: "same-origin",
        cache: "no-store",
        signal,
        headers: payload
          ? {
              "Content-Type": "application/json",
              ...(csrf ? { "X-CSRF-Token": csrf } : {}),
            }
          : undefined,
        body: payload ? JSON.stringify(payload) : undefined,
      });
      const data: unknown = await response.json();
      if (!response.ok) {
        const detail =
          data &&
          typeof data === "object" &&
          "detail" in data &&
          typeof data.detail === "string"
            ? data.detail
            : "認証処理に失敗しました。";
        throw new AuthError(response.status, detail);
      }
      return data;
    } catch (error) {
      if (signal?.aborted || error instanceof AuthError) throw error;
      throw new AuthError(
        0,
        "サーバーへ接続できません。時間をおいて再試行してください。",
      );
    }
  }
  async config(signal?: AbortSignal): Promise<AuthPolicy> {
    const data = await this.request("/config", undefined, signal);
    const value =
      data && typeof data === "object" && "policy" in data ? data.policy : null;
    if (!value || typeof value !== "object")
      throw new AuthError(502, "認証設定を読み込めません。");
    const policy = value as Record<string, unknown>;
    if (
      !Number.isInteger(policy.password_min_length) ||
      !Number.isInteger(policy.password_max_length) ||
      !Number.isInteger(policy.verification_minutes)
    )
      throw new AuthError(502, "認証設定を読み込めません。");
    return {
      passwordMinLength: policy.password_min_length as number,
      passwordMaxLength: policy.password_max_length as number,
      verificationMinutes: policy.verification_minutes as number,
    };
  }
  async session(signal?: AbortSignal) {
    try {
      return toSession(await this.request("/session", undefined, signal));
    } catch (error) {
      if (error instanceof AuthError && error.status === 401) return null;
      throw error;
    }
  }
  async register(email: string, signal?: AbortSignal) {
    const data = await this.request("/register", { email }, signal);
    if (
      !data ||
      typeof data !== "object" ||
      !("accepted" in data) ||
      data.accepted !== true
    )
      throw new AuthError(502, "確認メールの送信結果を読み込めません。");
  }
  async verify(token: string, password: string, signal?: AbortSignal) {
    const data = await this.request("/verify", { token, password }, signal);
    if (
      !data ||
      typeof data !== "object" ||
      !("verified" in data) ||
      data.verified !== true
    )
      throw new AuthError(502, "メール認証の結果を読み込めません。");
  }
  async login(email: string, password: string, signal?: AbortSignal) {
    return toSession(await this.request("/login", { email, password }, signal));
  }
  async logout(csrf: string, signal?: AbortSignal) {
    const data = await this.request("/logout", {}, signal, csrf);
    if (
      !data ||
      typeof data !== "object" ||
      !("authenticated" in data) ||
      data.authenticated !== false
    )
      throw new AuthError(502, "ログアウト結果を読み込めません。");
  }
}
