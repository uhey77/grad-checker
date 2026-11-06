import { useEffect, useRef, useState } from "react";
import {
  GraduationError,
  type CompletionAnswer,
  type GraduationResult,
  type GraduationUseCases,
} from "../../../../modules/requirements/public.ts";
import { errorMessage } from "../errorMessage.ts";

export function useCompletionAssessment(
  result: GraduationResult,
  useCases: GraduationUseCases,
  csrf: string,
  expire: () => void,
) {
  const [answers, setAnswers] = useState<CompletionAnswer[]>(() =>
    (result.completionConditions ?? []).map(({ code, status }) => ({
      code,
      status,
    })),
  );
  const [checked, setChecked] = useState<GraduationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  function change(code: string, status: CompletionAnswer["status"]) {
    setAnswers((current) =>
      current.map((answer) =>
        answer.code === code ? { code, status } : answer,
      ),
    );
    setChecked(null);
    setError("");
  }

  async function assess() {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError("");
    try {
      const saved = await useCases.createCheck.execute(
        result.dataRevision,
        csrf,
        controller.signal,
        answers,
      );
      if (controller.signal.aborted) return;
      if (
        saved.result.curriculum.id !== result.curriculum.id ||
        saved.result.curriculum.revision !== result.curriculum.revision ||
        saved.result.dataRevision !== result.dataRevision ||
        Object.keys(saved.result.ruleRevisions).length !==
          Object.keys(result.ruleRevisions).length ||
        Object.entries(result.ruleRevisions).some(
          ([id, revision]) => saved.result.ruleRevisions[id] !== revision,
        )
      )
        throw new GraduationError(
          409,
          "概要の取得後に保存データが更新されています。概要を再取得してください。",
        );
      setChecked(saved.result);
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (cause instanceof GraduationError && cause.status === 401) expire();
        setError(errorMessage(cause, "卒業要件を判定できませんでした。"));
      }
    } finally {
      if (!controller.signal.aborted) {
        request.current = null;
        setBusy(false);
      }
    }
  }
  return { answers, checked, busy, error, change, assess };
}
