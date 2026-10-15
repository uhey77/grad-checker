import { useState } from "react";
import type { AuthPolicy } from "../../modules/accounts/public.ts";

type Mode = "login" | "register" | "recover";
export function AuthForm({
  mode,
  policy,
  busy,
  submit,
}: {
  mode: Mode;
  policy: AuthPolicy;
  busy: boolean;
  submit: (loginName: string, password: string, recoveryCode: string) => void;
}) {
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [error, setError] = useState("");
  const settingPassword = mode !== "login";
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        setError("");
        if (!/^[A-Za-z0-9_]{3,32}$/.test(loginName)) {
          setError(
            "ユーザー名は半角英数字・アンダースコアの3〜32文字で入力してください。",
          );
          return;
        }
        if (
          settingPassword &&
          (Array.from(password).length < policy.passwordMinLength ||
            Array.from(password).length > policy.passwordMaxLength)
        ) {
          setError(
            `パスワードは${policy.passwordMinLength}〜${policy.passwordMaxLength}文字で入力してください。`,
          );
          return;
        }
        if (settingPassword && password !== confirmation) {
          setError("確認用パスワードが一致しません。");
          return;
        }
        submit(loginName, password, recoveryCode);
        setPassword("");
        setConfirmation("");
        setRecoveryCode("");
      }}
    >
      <fieldset disabled={busy}>
        <label htmlFor="auth-username">ユーザー名</label>
        <input
          id="auth-username"
          name="username"
          autoComplete="username"
          required
          minLength={3}
          maxLength={32}
          pattern="[A-Za-z0-9_]{3,32}"
          value={loginName}
          autoCapitalize="none"
          spellCheck={false}
          aria-describedby={mode === "register" ? "username-hint" : undefined}
          onChange={(event) => setLoginName(event.target.value)}
        />
        {mode === "register" ? (
          <p id="username-hint">
            半角英数字・アンダースコアの3〜32文字。大文字と小文字は区別しません。
          </p>
        ) : null}
        {mode === "recover" ? (
          <>
            <label htmlFor="auth-recovery">復旧コード</label>
            <input
              id="auth-recovery"
              name="recovery_code"
              type="password"
              autoComplete="off"
              required
              minLength={43}
              maxLength={43}
              value={recoveryCode}
              onChange={(event) => setRecoveryCode(event.target.value)}
            />
          </>
        ) : null}
        <label htmlFor="auth-password">
          {mode === "recover" ? "新しいパスワード" : "パスワード"}
        </label>
        <input
          id="auth-password"
          name="password"
          type="password"
          autoComplete={settingPassword ? "new-password" : "current-password"}
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        {settingPassword ? (
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
              ? "登録する"
              : mode === "recover"
                ? "パスワードを再設定する"
                : "ログイン"}
        </button>
      </fieldset>
    </form>
  );
}
