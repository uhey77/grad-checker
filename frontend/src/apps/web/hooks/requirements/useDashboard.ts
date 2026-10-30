import { useCallback, useEffect, useState } from "react";
import {
  GraduationError,
  type GraduationUseCases,
} from "../../../../modules/requirements/public.ts";
import { useRemote } from "../useRemote.ts";
import { errorMessage } from "../errorMessage.ts";

export function useDashboard(
  useCases: GraduationUseCases,
  active: boolean,
  revision: number,
  curriculumId: string | null,
  expire: () => void,
) {
  const [attempt, setAttempt] = useState(0);
  const key =
    active && curriculumId ? `${curriculumId}:${revision}:${attempt}` : null;
  const load = useCallback(
    async (signal: AbortSignal) => {
      const result = await useCases.dashboard.execute(signal);
      // 他タブの所属変更や古い応答を現在の課程の結果と取り違えない。
      if (
        result.curriculum.id !== curriculumId ||
        result.dataRevision < revision
      )
        throw new GraduationError(
          409,
          "所属または成績が更新されています。マイページと成績入力で保存済みデータを再取得してください。",
        );
      return result;
    },
    [useCases, curriculumId, revision],
  );
  const summary = useRemote(key, load, attempt);
  const failure = summary.status === "error" ? summary.error : null;
  useEffect(() => {
    if (failure instanceof GraduationError && failure.status === 401) expire();
  }, [failure, expire]);
  return {
    summary,
    retry: () => setAttempt((value) => value + 1),
    message: (error: unknown) =>
      errorMessage(error, "卒業要件の概要を取得できませんでした。"),
  };
}
