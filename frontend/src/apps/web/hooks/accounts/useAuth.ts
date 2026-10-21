import { useCallback, useEffect, useRef, useState } from "react";
import {
  AuthError,
  type AuthSession,
  type AuthPolicy,
  type AuthUseCases,
} from "../../../../modules/accounts/public.ts";
import { errorMessage } from "../errorMessage.ts";
import { useExclusiveAction } from "../useExclusiveAction.ts";

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
  const [attempt, setAttempt] = useState(0);
  const { busy, running, abort, run: runExclusive } = useExclusiveAction();
  const channel = useRef<BroadcastChannel | null>(null);
  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const broadcast = new BroadcastChannel("grad-checker-auth");
    channel.current = broadcast;
    broadcast.onmessage = (event) => {
      if (event.data === "logout") {
        abort();
        setState({ session: null, status: "loading", error: "" });
        setAttempt((value) => value + 1);
      }
    };
    return () => {
      broadcast.close();
      channel.current = null;
    };
  }, [abort]);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      useCases.session.execute(controller.signal),
      useCases.config.execute(controller.signal),
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
            error: errorMessage(error, "認証情報を取得できません。"),
          });
      },
    );
    return () => {
      controller.abort();
      abort();
    };
  }, [useCases, attempt, abort]);
  const expire = useCallback(() => {
    abort();
    setState((previous) => ({
      ...previous,
      status: "ready",
      session: null,
      error: "ログインの有効期限が切れました。再度ログインしてください。",
    }));
  }, [abort]);
  useEffect(() => {
    const session = state.session;
    if (!session) return;
    const timer = window.setTimeout(
      expire,
      Math.max(0, Date.parse(session.expiresAt) - Date.now()),
    );
    let checking: AbortController | null = null;
    const check = () => {
      if (document.visibilityState === "hidden") return;
      if (Date.parse(session.expiresAt) <= Date.now()) {
        expire();
        return;
      }
      if (checking || running()) return;
      const controller = new AbortController();
      checking = controller;
      void useCases.session
        .execute(controller.signal)
        .then(
          (current) => {
            if (controller.signal.aborted || running()) return;
            if (!current) expire();
            else
              setState((previous) =>
                previous.session === session
                  ? { ...previous, session: current }
                  : previous,
              );
          },
          () => {
            // 一時的な通信障害で有効なセッションを破棄しない。
          },
        )
        .finally(() => {
          if (checking === controller) checking = null;
        });
    };
    window.addEventListener("focus", check);
    document.addEventListener("visibilitychange", check);
    return () => {
      checking?.abort();
      window.clearTimeout(timer);
      window.removeEventListener("focus", check);
      document.removeEventListener("visibilitychange", check);
    };
  }, [state.session, expire, useCases, running]);

  function run<T>(
    operation: (signal: AbortSignal) => Promise<T>,
    done: (result: T) => void,
  ) {
    return runExclusive(
      (signal) => {
        setState((previous) => ({ ...previous, error: "" }));
        return operation(signal);
      },
      {
        onSuccess: done,
        onError: (error) =>
          setState((previous) => ({
            ...previous,
            session:
              error instanceof AuthError && error.status === 401
                ? null
                : previous.session,
            error: errorMessage(error, "認証処理に失敗しました。"),
          })),
      },
    );
  }
  return {
    ...state,
    expire,
    busy,
    clearError: () => setState((previous) => ({ ...previous, error: "" })),
    retry: () => {
      setState({ status: "loading", session: null, error: "" });
      setAttempt((value) => value + 1);
    },
    login: (loginName: string, password: string) =>
      run(
        (signal) => useCases.login.execute(loginName, password, signal),
        (session) =>
          setState((previous) => ({
            ...previous,
            status: "ready",
            session,
            error: "",
          })),
      ),
    register: (
      loginName: string,
      password: string,
      done: (code: string) => void,
    ) =>
      run(
        (signal) => useCases.register.execute(loginName, password, signal),
        done,
      ),
    recover: (
      loginName: string,
      code: string,
      password: string,
      done: (code: string) => void,
    ) =>
      run(
        (signal) => useCases.recover.execute(loginName, code, password, signal),
        (result) => {
          channel.current?.postMessage("logout");
          done(result);
        },
      ),
    logout: () => {
      if (state.session)
        void run(
          (signal) => useCases.logout.execute(state.session!.csrfToken, signal),
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
