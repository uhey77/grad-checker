import { useCallback, useEffect, useState } from "react";
import {
  GraduationError,
  type GraduationUseCases,
} from "../../../../modules/requirements/public.ts";
import { errorMessage } from "../errorMessage.ts";
import { useRemote } from "../useRemote.ts";

const CHECK_PAGE_SIZE = 20;

// 本人の判定履歴の一覧と、選択した過去の判定の詳細を取得する。取得では履歴を作らない。
export function useCheckHistory(
  useCases: GraduationUseCases,
  active: boolean,
  expire: () => void,
) {
  const [offset, setOffset] = useState(0);
  const [listAttempt, setListAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailAttempt, setDetailAttempt] = useState(0);
  const loadPage = useCallback(
    (signal: AbortSignal) =>
      useCases.listChecks.execute({ limit: CHECK_PAGE_SIZE, offset }, signal),
    [useCases, offset],
  );
  const loadDetail = useCallback(
    (signal: AbortSignal) =>
      selectedId
        ? useCases.getCheck.execute(selectedId, signal)
        : Promise.reject(new Error("判定履歴が選択されていません。")),
    [useCases, selectedId],
  );
  // 画面離脱・ページ切替では古い一覧の取得を中断し、表示を上書きしない。
  const page = useRemote(
    active ? `checks:${offset}` : null,
    loadPage,
    listAttempt,
  );
  const detail = useRemote(
    active && selectedId ? `check:${selectedId}` : null,
    loadDetail,
    detailAttempt,
  );
  const failures = [page, detail].flatMap((remote) =>
    remote.status === "error" ? [remote.error] : [],
  );
  const unauthenticated = failures.some(
    (error) => error instanceof GraduationError && error.status === 401,
  );
  useEffect(() => {
    if (unauthenticated) expire();
  }, [unauthenticated, expire]);

  return {
    page:
      page.status === "ready"
        ? { status: "ready" as const, data: page.data }
        : page.status === "error"
          ? {
              status: "error" as const,
              message: errorMessage(
                page.error,
                "判定履歴を取得できませんでした。",
              ),
            }
          : { status: "loading" as const },
    detail: !selectedId
      ? null
      : detail.status === "ready"
        ? { status: "ready" as const, check: detail.data }
        : detail.status === "error"
          ? {
              status: "error" as const,
              message: errorMessage(
                detail.error,
                "過去の判定を取得できませんでした。",
              ),
            }
          : { status: "loading" as const },
    pageSize: CHECK_PAGE_SIZE,
    selectedId,
    select: setSelectedId,
    showLatest: () => setSelectedId(null),
    showPage: setOffset,
    retryPage: () => setListAttempt((attempt) => attempt + 1),
    retryDetail: () => setDetailAttempt((attempt) => attempt + 1),
    // 新しい判定を保存した後は、最新の履歴が載る先頭ページを取り直す。
    refresh: () => {
      setOffset(0);
      setListAttempt((attempt) => attempt + 1);
    },
  };
}
