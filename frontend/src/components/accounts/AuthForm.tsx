import { useState } from "react";
import type { AuthPolicy } from "../../modules/accounts/public.ts";

type Mode = "login" | "register" | "verify";
export function AuthForm({
  mode,
  policy,
  busy,
  submit,
}: {
  mode: Mode;
  policy: AuthPolicy;
  busy: boolean;
  submit: (email: string, password: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        setError("");
        if (mode !== "verify" && !/^[^@\s]+@edu\.teu\.ac\.jp$/i.test(email)) {
          setError("大学で発行されたメールアドレスを入力してください。");
          return;
        }
        if (mode === "verify" && password !== confirmation) {
          setError("確認用パスワードが一致しません。");
          return;
        }
        submit(email, password);
        setPassword("");
        setConfirmation("");
      }}
    >
      <fieldset disabled={busy}>
        {mode !== "verify" ? (
          <>
            <label htmlFor="auth-email">大学メールアドレス</label>
            <input
              id="auth-email"
              name="email"
              type="email"
              autoComplete="username"
              placeholder="例：student@edu.teu.ac.jp"
              required
              maxLength={254}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </>
        ) : null}
        {mode !== "register" ? (
          <>
            <label htmlFor="auth-password">
              {mode === "verify" ? "新しいパスワード" : "パスワード"}
            </label>
            <input
              id="auth-password"
              name="password"
              type="password"
              autoComplete={
                mode === "verify" ? "new-password" : "current-password"
              }
              required
              minLength={
                mode === "verify" ? policy.passwordMinLength : undefined
              }
              maxLength={policy.passwordMaxLength}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </>
        ) : null}
        {mode === "verify" ? (
          <>
            <p>
              {policy.passwordMinLength}〜{policy.passwordMaxLength}
              文字で設定してください。
            </p>
            <label htmlFor="auth-confirm">パスワード（確認）</label>
            <input
              id="auth-confirm"
              name="confirmation"
              type="password"
              autoComplete="new-password"
              required
              maxLength={policy.passwordMaxLength}
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
            />
          </>
        ) : null}
        {error ? <p role="alert">{error}</p> : null}
        <button type="submit">
          {busy
            ? "処理中…"
            : mode === "register"
              ? "確認メールを送る"
              : mode === "verify"
                ? "登録を完了する"
                : "ログイン"}
        </button>
      </fieldset>
    </form>
  );
}
