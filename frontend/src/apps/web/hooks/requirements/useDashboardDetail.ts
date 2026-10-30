import { useCallback, useEffect } from "react";
import {
  GraduationError,
  type DashboardResult,
  type GraduationUseCases,
} from "../../../../modules/requirements/public.ts";
import { useRemote } from "../useRemote.ts";

// 不足科目の表示に使うため、概要と同じ版の詳細を取得する。
export function useDashboardDetail(
  useCases: GraduationUseCases,
  current: DashboardResult | null,
  active: boolean,
  expire: () => void,
) {
  const load = useCallback(
    async (signal: AbortSignal) => {
      const result = await useCases.evaluate.execute(signal);
      if (
        !current ||
        result.curriculum.id !== current.curriculum.id ||
        result.dataRevision !== current.dataRevision ||
        result.curriculum.revision !== current.curriculumRevision ||
        Object.keys(result.ruleRevisions).length !==
          Object.keys(current.ruleRevisions).length ||
        Object.entries(current.ruleRevisions).some(
          ([id, revision]) => result.ruleRevisions[id] !== revision,
        )
      )
        throw new GraduationError(
          409,
          "概要の取得後に保存データが更新されています。概要を再取得してください。",
        );
      return result;
    },
    [useCases, current],
  );
  const detail = useRemote(
    active && current
      ? `${current.curriculum.id}:${current.dataRevision}:${current.evaluatedAt}`
      : null,
    load,
    0,
  );
  const failure = detail.status === "error" ? detail.error : null;
  useEffect(() => {
    if (failure instanceof GraduationError && failure.status === 401) expire();
  }, [failure, expire]);
  return detail;
}
