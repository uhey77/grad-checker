import { useEffect, useState } from "react";
import {
  GraduationError,
  type GraduationResult,
  type GraduationUseCases,
} from "../../modules/requirements/public.ts";
import { errorMessage } from "../errorMessage";
import { useExclusiveAction } from "../useExclusiveAction";

export function useGraduationCheck(
  useCases: GraduationUseCases,
  revision: number,
  curriculumId: string,
  active: boolean,
  blocked: boolean,
  expire: () => void,
  reportRevision: (revision: number) => void,
) {
  const [state, setState] = useState<{
    key: string;
    result?: GraduationResult;
    error?: string;
  } | null>(null);
  const { busy, run, abort, running } = useExclusiveAction();
  const key = `${curriculumId}:${revision}`;
  // 所属・成績の変更、未保存の編集、画面離脱は進行中の判定を中断する。
  useEffect(() => () => abort(), [key, active, blocked, abort]);

  async function check() {
    if (!active || blocked || running()) return;
    setState(null);
    await run((signal) => useCases.evaluate(signal), {
      onSuccess: (result) => {
        if (
          result.dataRevision !== revision ||
          result.curriculum.id !== curriculumId
        ) {
          reportRevision(result.dataRevision);
          setState({
            key,
            error:
              "成績または所属が更新されています。保存済みの成績を再取得してから判定してください。",
          });
          return;
        }
        setState({ key, result });
      },
      onError: (error) => {
        if (error instanceof GraduationError && error.status === 401) expire();
        setState({
          key,
          error: errorMessage(error, "卒業要件を判定できませんでした。"),
        });
      },
    });
  }
  const visible = active && !blocked && state?.key === key ? state : null;
  return { busy, check, result: visible?.result, error: visible?.error };
}
