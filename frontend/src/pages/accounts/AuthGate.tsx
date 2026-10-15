import { useState, type ReactNode } from "react";
import type { AuthUseCases } from "../../modules/accounts/public.ts";
import { useAuth } from "../../hooks/accounts/useAuth";
import { AuthForm } from "../../components/accounts/AuthForm";

export function AuthGate({
  useCases,
  children,
}: {
  useCases: AuthUseCases;
  children: ReactNode;
}) {
  const auth = useAuth(useCases);
  const [mode, setMode] = useState<"login" | "register" | "recover">("login");
  const [notice, setNotice] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [saved, setSaved] = useState(false);
  if (auth.status === "loading")
    return (
      <main>
        <p role="status">ログイン状態を確認しています…</p>
      </main>
    );
  if (auth.status === "error" || !auth.policy)
    return (
      <main>
        <p role="alert">{auth.error}</p>
        <button onClick={auth.retry}>再試行</button>
      </main>
    );
  if (auth.session)
    return (
      <>
        <div className="auth-toolbar">
          <span>{auth.session.student.loginName}</span>
          <button disabled={auth.busy} onClick={auth.logout}>
            ログアウト
          </button>
        </div>
        {auth.error ? (
          <p className="auth-message" role="alert">
            {auth.error}
          </p>
        ) : null}
        {children}
      </>
    );
  const showRecovery = (code: string) => {
    setRecoveryCode(code);
    setSaved(false);
    setNotice(
      mode === "register"
        ? "登録が完了しました。"
        : "パスワードを再設定し、すべての端末からログアウトしました。",
    );
  };
  return (
    <main className="auth-page">
      <section className="auth-card">
        <h1>
          {recoveryCode
            ? "復旧コードを保管してください"
            : mode === "register"
              ? "新規登録"
              : mode === "recover"
                ? "パスワードの再設定"
                : "ログイン"}
        </h1>
        {notice ? <p role="status">{notice}</p> : null}
        {recoveryCode ? (
          <>
            <p>
              このコードは一度だけ表示します。パスワードを忘れたときに必要です。安全な場所に保管してください。
            </p>
            <label htmlFor="issued-recovery">復旧コード</label>
            <input
              id="issued-recovery"
              value={recoveryCode}
              readOnly
              onFocus={(event) => event.target.select()}
            />
            <p>
              以前の復旧コードは使えません。コードとパスワードを両方失った場合、アカウントは復旧できません。
            </p>
            <label className="recovery-confirm">
              <input
                type="checkbox"
                checked={saved}
                onChange={(event) => setSaved(event.target.checked)}
              />
              復旧コードを保管しました
            </label>
            <button
              disabled={!saved}
              onClick={() => {
                setRecoveryCode("");
                setMode("login");
                setNotice("ユーザー名とパスワードでログインしてください。");
              }}
            >
              ログインへ進む
            </button>
          </>
        ) : (
          <>
            {auth.error ? <p role="alert">{auth.error}</p> : null}
            <AuthForm
              key={mode}
              mode={mode}
              policy={auth.policy}
              busy={auth.busy}
              submit={(loginName, password, code) => {
                setNotice("");
                if (mode === "register")
                  void auth.register(loginName, password, showRecovery);
                else if (mode === "recover")
                  void auth.recover(loginName, code, password, showRecovery);
                else void auth.login(loginName, password);
              }}
            />
            {mode === "login" ? (
              <>
                <button
                  className="auth-switch"
                  disabled={auth.busy}
                  onClick={() => {
                    setNotice("");
                    setMode("register");
                  }}
                >
                  新規登録
                </button>
                <button
                  className="auth-switch"
                  disabled={auth.busy}
                  onClick={() => {
                    setNotice("");
                    setMode("recover");
                  }}
                >
                  パスワードを忘れた場合
                </button>
              </>
            ) : (
              <button
                className="auth-switch"
                disabled={auth.busy}
                onClick={() => {
                  setNotice("");
                  setMode("login");
                }}
              >
                ログインへ戻る
              </button>
            )}
          </>
        )}
      </section>
    </main>
  );
}
