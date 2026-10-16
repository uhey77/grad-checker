import { useEffect, useRef, useState, type ReactNode } from "react";
import type {
  AuthSession,
  AuthUseCases,
} from "../../modules/accounts/public.ts";
import { useAuth } from "../../hooks/accounts/useAuth";
import { RecoveryCode } from "../../components/accounts/RecoveryCode";
import { AuthForm } from "../../components/accounts/AuthForm";
import {
  ErrorState,
  FormError,
  LoadingState,
} from "../../components/StatusPanels";

export function AuthGate({
  useCases,
  children,
}: {
  useCases: AuthUseCases;
  children: (session: AuthSession, expire: () => void) => ReactNode;
}) {
  const auth = useAuth(useCases);
  const [mode, setMode] = useState<"login" | "register" | "recover">("login");
  const [notice, setNotice] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [mode, recoveryCode, auth.status, auth.session]);
  const switchMode = (next: typeof mode) => {
    setNotice("");
    auth.clearError();
    setMode(next);
  };
  if (auth.status === "loading")
    return (
      <main id="main-content">
        <LoadingState>ログイン状態を確認しています…</LoadingState>
      </main>
    );
  if (auth.status === "error" || !auth.policy)
    return (
      <main id="main-content">
        <ErrorState
          message={auth.error}
          actionLabel="再試行"
          onAction={auth.retry}
        />
      </main>
    );
  if (auth.session)
    return (
      <>
        <div className="auth-toolbar">
          <span>
            ログイン中：<strong>{auth.session.student.loginName}</strong>
          </span>
          <button disabled={auth.busy} onClick={auth.logout}>
            ログアウト
          </button>
        </div>
        {auth.error ? (
          <div className="auth-message">
            <FormError>{auth.error}</FormError>
          </div>
        ) : null}
        {children(auth.session, auth.expire)}
      </>
    );
  const showRecovery = (code: string) => {
    setRecoveryCode(code);

    setNotice(
      mode === "register"
        ? "登録が完了しました。"
        : "パスワードを再設定し、すべての端末からログアウトしました。",
    );
  };
  return (
    <main id="main-content" className="auth-page">
      <section className="auth-card">
        <h1 ref={heading} tabIndex={-1}>
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
          <RecoveryCode
            code={recoveryCode}
            proceed={() => {
              setRecoveryCode("");
              switchMode("login");
              setNotice("ユーザー名とパスワードでログインしてください。");
            }}
          />
        ) : (
          <>
            {auth.error ? <FormError>{auth.error}</FormError> : null}
            <p className="auth-help">
              {mode === "register"
                ? "このアプリ専用のアカウントを作成します。登録後に復旧コードを発行します。"
                : mode === "recover"
                  ? "ユーザー名と保管した復旧コードで、新しいパスワードを設定します。成功すると以前の復旧コードは使えなくなります。"
                  : "アプリ専用のユーザー名とパスワードを入力してください。"}
            </p>
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
                    switchMode("register");
                  }}
                >
                  新規登録
                </button>
                <button
                  className="auth-switch"
                  disabled={auth.busy}
                  onClick={() => {
                    switchMode("recover");
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
                  switchMode("login");
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
