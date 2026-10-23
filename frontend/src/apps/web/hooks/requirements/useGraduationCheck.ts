import { useEffect, useState } from "react";
import {
  GraduationError,
  type GraduationUseCases,
  type SavedCheck,
  type CompletionAnswer,
} from "../../../../modules/requirements/public.ts";
import { errorMessage } from "../errorMessage.ts";
import { useExclusiveAction } from "../useExclusiveAction.ts";

// 保存済みの成績版で卒業要件を判定し、結果を本人の判定履歴に保存する。
export function useGraduationCheck(
  useCases: GraduationUseCases,
  revision: number,
  curriculumId: string,
  csrf: string,
  active: boolean,
  blocked: boolean,
  expire: () => void,
  saved: (check: SavedCheck) => void,
) {
  const [state, setState] = useState<{
    key: string;
    check?: SavedCheck;
    error?: string;
  } | null>(null);
  const { busy, run, abort, running } = useExclusiveAction();
  const key = `${curriculumId}:${revision}`;
  // 所属・保存済み成績の変更、概要の再取得、画面離脱は進行中の判定を中断する。
  useEffect(() => () => abort(), [key, active, blocked, abort]);

  async function check(answers?: CompletionAnswer[]) {
    if (!active || blocked || running()) return;
    setState(null);
    await run(
      (signal) => useCases.createCheck.execute(revision, csrf, signal, answers),
      {
        onSuccess: (check) => {
          // 履歴には保存されているため、表示中の課程と異なっても一覧は更新する。
          saved(check);
          if (check.result.curriculum.id !== curriculumId) {
            setState({
              key,
              error:
                "所属が更新されています。保存済みの成績を再取得してから判定してください。",
            });
            return;
          }
          setState({ key, check });
        },
        onError: (error) => {
          if (error instanceof GraduationError && error.status === 401)
            expire();
          setState({
            key,
            error: errorMessage(error, "卒業要件を判定できませんでした。"),
          });
        },
      },
    );
  }
  const visible = active && !blocked && state?.key === key ? state : null;
  return {
    busy,
    check,
    saved: visible?.check,
    error: visible?.error,
    reset: () => {
      abort();
      setState(null);
    },
  };
}
