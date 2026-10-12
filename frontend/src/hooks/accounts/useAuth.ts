import { useCallback, useEffect, useRef, useState } from "react";
import {
  AuthError,
  type AuthSession,
  type AuthPolicy,
  type AuthUseCases,
} from "../../modules/accounts/public.ts";

type AuthState = {
  status: "loading" | "ready" | "error";
  session: AuthSession | null;
  policy?: AuthPolicy;
  error: string;
};
export function useAuth(useCases: AuthUseCases) {
  const [state, setState] = useState<AuthState>({
    status: "loading",
    session: null,
    error: "",
  });
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const action = useRef<AbortController | null>(null);
  const channel = useRef<BroadcastChannel | null>(null);
  useEffect(() => {
    const broadcast = new BroadcastChannel("grad-checker-auth");
    channel.current = broadcast;
    broadcast.onmessage = (event) => {
      if (event.data === "logout") {
        action.current?.abort();
        action.current = null;
        setBusy(false);
        setState({ session: null, status: "loading", error: "" });
        setAttempt((value) => value + 1);
      }
    };
    return () => {
      broadcast.close();
      channel.current = null;
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      useCases.session(controller.signal),
      useCases.config(controller.signal),
    ]).then(
      ([session, policy]) => {
        if (!controller.signal.aborted)
          setState({ status: "ready", session, policy, error: "" });
      },
      (error) => {
        if (!controller.signal.aborted)
          setState({
            status: "error",
            session: null,
            error:
              error instanceof Error
                ? error.message
                : "認証情報を取得できません。",
          });
      },
    );
    return () => {
      controller.abort();
      action.current?.abort();
    };
  }, [useCases, attempt]);
  const expire = useCallback(
    () =>
      setState((previous) => ({
        ...previous,
        status: "ready",
        session: null,
        error: "ログインの有効期限が切れました。再度ログインしてください。",
      })),
    [],
  );
  useEffect(() => {
    const session = state.session;
    if (!session) return;
    const timer = window.setTimeout(
      expire,
      Math.max(0, Date.parse(session.expiresAt) - Date.now()),
    );
    const check = () => {
      if (Date.parse(session.expiresAt) <= Date.now()) expire();
    };
    window.addEventListener("focus", check);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("focus", check);
    };
  }, [state.session, expire]);
  async function run<T>(
    operation: (signal: AbortSignal) => Promise<T>,
    done: (result: T) => void,
  ) {
    if (action.current) return;
    const controller = new AbortController();
    action.current = controller;
    setBusy(true);
    setState((previous) => ({ ...previous, error: "" }));
    try {
      const result = await operation(controller.signal);
      if (!controller.signal.aborted) done(result);
    } catch (error) {
      if (!controller.signal.aborted)
        setState((previous) => ({
          ...previous,
          session:
            error instanceof AuthError && error.status === 401
              ? null
              : previous.session,
          error:
            error instanceof Error ? error.message : "認証処理に失敗しました。",
        }));
    } finally {
      if (action.current === controller) action.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return {
    ...state,
    busy,
    retry: () => {
      setState({ status: "loading", session: null, error: "" });
      setAttempt((value) => value + 1);
    },
    login: (email: string, password: string) =>
      run(
        (signal) => useCases.login(email, password, signal),
        (session) =>
          setState((previous) => ({
            ...previous,
            status: "ready",
            session,
            error: "",
          })),
      ),
    register: (email: string, done: () => void) =>
      run((signal) => useCases.register(email, signal), done),
    verify: (token: string, password: string, done: () => void) =>
      run((signal) => useCases.verify(token, password, signal), done),
    logout: () => {
      if (state.session)
        void run(
          (signal) => useCases.logout(state.session!.csrfToken, signal),
          () => {
            channel.current?.postMessage("logout");
            setState((previous) => ({
              ...previous,
              status: "ready",
              session: null,
              error: "",
            }));
          },
        );
    },
  };
}
