import { useEffect, useState } from "react";

type Remote<T> =
  | { key: string | null; status: "loading" }
  | { key: string; status: "ready"; data: T }
  | { key: string; status: "error"; message: string };

export function useRemote<T>(
  key: string | null,
  load: (signal: AbortSignal) => Promise<T>,
  attempt: number,
): Remote<T> {
  const [state, setState] = useState<Remote<T>>({ key, status: "loading" });
  useEffect(() => {
    if (!key) return;
    const requestKey = key;
    const controller = new AbortController();
    // 同じ課程の再試行でも、通信開始時にローディング表示へ戻す。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState({ key, status: "loading" });
    void load(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted)
          setState({ key: requestKey, status: "ready", data });
      },
      (error: unknown) => {
        if (!controller.signal.aborted)
          setState({
            key: requestKey,
            status: "error",
            message:
              error instanceof Error
                ? error.message
                : "科目一覧を読み込めませんでした。",
          });
      },
    );
    return () => controller.abort();
  }, [key, load, attempt]);
  // 課程切替の直後にも、前の課程の科目を表示しない。
  return state.key === key ? state : { key, status: "loading" };
}
