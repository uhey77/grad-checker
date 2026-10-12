import { useState, type ReactNode } from "react";
import type { AuthUseCases } from "../../modules/accounts/public.ts";
import { useAuth } from "../../hooks/accounts/useAuth";
import { AuthForm } from "../../components/accounts/AuthForm";

export function AuthGate({
  useCases,
  verificationToken,
  children,
}: {
  useCases: AuthUseCases;
  verificationToken: string;
  children: ReactNode;
}) {
  const auth = useAuth(useCases);
  const [mode, setMode] = useState<"login" | "register" | "verify">(
    verificationToken ? "verify" : "login",
  );
  const [notice, setNotice] = useState("");
  const [token, setToken] = useState(verificationToken);
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
  if (auth.session && mode === "verify")
    return (
      <main className="auth-page">
        <section className="auth-card">
          <h1>メール認証</h1>
          <p>
            {auth.session.student.email}{" "}
            でログイン中です。新しい登録を進めるにはログアウトしてください。
          </p>
          {auth.error ? <p role="alert">{auth.error}</p> : null}
          <button disabled={auth.busy} onClick={auth.logout}>
            ログアウト
          </button>
        </section>
      </main>
    );
  if (auth.session && mode !== "verify")
    return (
      <>
        <div className="auth-toolbar">
          <span>{auth.session.student.email}</span>
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
  return (
    <main className="auth-page">
      <section className="auth-card">
        <h1>
          {mode === "register"
            ? "新規登録"
            : mode === "verify"
              ? "メール認証・パスワード設定"
              : "ログイン"}
        </h1>
        <p>
          {mode === "register"
            ? "大学のメールアドレスに確認リンクを送ります。"
            : mode === "verify"
              ? `確認リンクの有効期限は${auth.policy.verificationMinutes}分です。パスワードを設定して登録を完了してください。`
              : "メール認証を済ませたアドレスでログインしてください。"}
        </p>
        {notice ? <p role="status">{notice}</p> : null}
        {auth.error ? <p role="alert">{auth.error}</p> : null}
        <AuthForm
          key={mode}
          mode={mode}
          policy={auth.policy}
          busy={auth.busy}
          submit={(email, password) => {
            setNotice("");
            if (mode === "register")
              void auth.register(email, () =>
                setNotice(
                  "登録可能なアドレスには確認メールを送信しました。受信箱・迷惑メールをご確認ください。登録済みの場合はログインしてください。",
                ),
              );
            else if (mode === "verify")
              void auth.verify(token, password, () => {
                setToken("");
                setMode("login");
                setNotice(
                  "登録が完了しました。メールアドレスと設定したパスワードでログインしてください。",
                );
              });
            else void auth.login(email, password);
          }}
        />
        <button
          className="auth-switch"
          disabled={auth.busy}
          onClick={() => {
            setNotice("");
            setToken("");
            setMode(mode === "login" ? "register" : "login");
          }}
        >
          {mode === "login" ? "新規登録・確認メールの再送" : "ログインへ戻る"}
        </button>
      </section>
    </main>
  );
}
