import { useCallback, useRef, useState } from "react";

interface Handlers<T> {
  onSuccess: (result: T) => void;
  onError: (error: unknown) => void;
}

// 保存などの操作を一度に一つだけ実行する。中断した操作の結果・失敗は画面へ反映しない。
export function useExclusiveAction() {
  const current = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const running = useCallback(() => current.current !== null, []);
  const abort = useCallback(() => {
    current.current?.abort();
    current.current = null;
    setBusy(false);
  }, []);
  const run = useCallback(
    async <T>(
      operation: (signal: AbortSignal) => Promise<T>,
      { onSuccess, onError }: Handlers<T>,
    ) => {
      if (current.current) return;
      const controller = new AbortController();
      current.current = controller;
      setBusy(true);
      try {
        const result = await operation(controller.signal);
        if (!controller.signal.aborted) onSuccess(result);
      } catch (error) {
        if (!controller.signal.aborted) onError(error);
      } finally {
        if (current.current === controller) current.current = null;
        if (!controller.signal.aborted) setBusy(false);
      }
    },
    [],
  );
  return { busy, running, abort, run };
}
