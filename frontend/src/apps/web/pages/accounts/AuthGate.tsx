import { useTranslation } from "react-i18next";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type {
  AuthSession,
  AuthUseCases,
} from "../../../../modules/accounts/public.ts";
import { AppLayout } from "../../layouts/AppLayout.tsx";
import { useAuth } from "../../hooks/accounts/useAuth.ts";
import { RecoveryCode } from "../../components/accounts/RecoveryCode.tsx";
import { AuthForm } from "../../components/accounts/AuthForm.tsx";
import {
  ErrorState,
  FormError,
  LoadingState,
} from "../../components/StatusPanels.tsx";
export type AuthControls = {
  busy: boolean;
  error: string;
  logout: () => void;
};
export function AuthGate({
  useCases,
  children,
}: {
  useCases: AuthUseCases;
  children: (
    session: AuthSession,
    expire: () => void,
    controls: AuthControls,
  ) => ReactNode;
}) {
  const { t } = useTranslation();
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
      <AppLayout>
        <main id="main-content">
          <LoadingState>{t("ログイン状態を確認しています…")}</LoadingState>
        </main>
      </AppLayout>
    );
  if (auth.status === "error" || !auth.policy)
    return (
      <AppLayout>
        <main id="main-content">
          <ErrorState
            message={auth.error}
            actionLabel={t("再試行")}
            onAction={auth.retry}
          />
        </main>
      </AppLayout>
    );
  if (auth.session)
    return children(auth.session, auth.expire, {
      busy: auth.busy,
      error: auth.error,
      logout: auth.logout,
    });
  const showRecovery = (code: string) => {
    setRecoveryCode(code);
    setNotice(
      mode === "register"
        ? "登録が完了しました。"
        : "パスワードを再設定し、すべての端末からログアウトしました。",
    );
  };
  return (
    <AppLayout>
      <main id="main-content" className="auth-page">
        <section className="auth-card">
          <h1 ref={heading} tabIndex={-1}>
            {recoveryCode
              ? t("復旧コードを保管してください")
              : mode === "register"
                ? t("新規登録")
                : mode === "recover"
                  ? t("パスワードの再設定")
                  : t("ログイン")}
          </h1>
          {notice ? <p role="status">{t(notice)}</p> : null}
          {recoveryCode ? (
            <RecoveryCode
              code={recoveryCode}
              proceed={() => {
                setRecoveryCode("");
                switchMode("login");
                setNotice(t("ユーザー名とパスワードでログインしてください。"));
              }}
            />
          ) : (
            <>
              {auth.error ? <FormError>{auth.error}</FormError> : null}
              <p className="auth-help">
                {mode === "register"
                  ? t(
                      "このアプリ専用のアカウントを作成します。登録後に復旧コードを発行します。",
                    )
                  : mode === "recover"
                    ? t(
                        "ユーザー名と保管した復旧コードで、新しいパスワードを設定します。成功すると以前の復旧コードは使えなくなります。",
                      )
                    : t(
                        "アプリ専用のユーザー名とパスワードを入力してください。",
                      )}
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
                    {t("新規登録")}
                  </button>
                  <button
                    className="auth-switch"
                    disabled={auth.busy}
                    onClick={() => {
                      switchMode("recover");
                    }}
                  >
                    {t("パスワードを忘れた場合")}
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
                  {t("ログインへ戻る")}
                </button>
              )}
            </>
          )}
        </section>
      </main>
    </AppLayout>
  );
}
