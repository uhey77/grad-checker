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
  const [error, setError] = useState({ field: "", message: "" });
  const settingPassword = mode !== "login";
  const errorProps = (field: string, hint?: string) => ({
    "aria-invalid": error.field === field || undefined,
    "aria-describedby":
      [hint, error.field === field ? "auth-input-error" : ""]
        .filter(Boolean)
        .join(" ") || undefined,
  });
  return (
    <form
      noValidate
      aria-busy={busy}
      onSubmit={(event) => {
        event.preventDefault();
        if (busy) return;
        const invalid = (field: string, message: string) => {
          setError({ field, message });
          const input = event.currentTarget.elements.namedItem(field);
          if (input instanceof HTMLInputElement) input.focus();
        };
        if (!/^[A-Za-z0-9_]{3,32}$/.test(loginName)) {
          invalid(
            "username",
            "ユーザー名は半角英数字・アンダースコアの3〜32文字で入力してください。",
          );
          return;
        }
        if (mode === "recover" && !/^[A-Za-z0-9_-]{43}$/.test(recoveryCode)) {
          invalid(
            "recovery_code",
            "復旧コードは保管した43文字を入力してください。",
          );
          return;
        }
        if (
          !password ||
          (settingPassword &&
            (Array.from(password).length < policy.passwordMinLength ||
              Array.from(password).length > policy.passwordMaxLength))
        ) {
          invalid(
            "password",
            settingPassword
              ? `パスワードは${policy.passwordMinLength}〜${policy.passwordMaxLength}文字で入力してください。`
              : "パスワードを入力してください。",
          );
          return;
        }
        if (settingPassword && password !== confirmation) {
          invalid("confirmation", "確認用パスワードが一致しません。");
          return;
        }
        setError({ field: "", message: "" });
        // 失敗したときに再入力を求めない。成功時はフォームの離脱で破棄する。
        submit(loginName, password, recoveryCode);
      }}
    >
      <fieldset disabled={busy}>
        <label htmlFor="auth-username">ユーザー名</label>
        <input
          id="auth-username"
          name="username"
          autoComplete="username"
          required
          maxLength={32}
          value={loginName}
          autoCapitalize="none"
          spellCheck={false}
          {...errorProps("username", "username-hint")}
          onChange={(event) => setLoginName(event.target.value)}
        />
        <p id="username-hint" className="field-hint">
          半角英数字・アンダースコアの3〜32文字。大文字と小文字は区別しません。
        </p>
        {mode === "recover" ? (
          <>
            <label htmlFor="auth-recovery">復旧コード</label>
            <input
              id="auth-recovery"
              name="recovery_code"
              type="password"
              autoComplete="off"
              required
              value={recoveryCode}
              {...errorProps("recovery_code")}
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
          {...errorProps(
            "password",
            settingPassword ? "password-hint" : undefined,
          )}
          onChange={(event) => setPassword(event.target.value)}
        />
        {settingPassword ? (
          <>
            <p id="password-hint" className="field-hint">
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
              {...errorProps("confirmation")}
              onChange={(event) => setConfirmation(event.target.value)}
            />
          </>
        ) : null}
        {error.message ? (
          <p id="auth-input-error" className="form-error" role="alert">
            {error.message}
          </p>
        ) : null}
        <button className="primary-button" type="submit">
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
