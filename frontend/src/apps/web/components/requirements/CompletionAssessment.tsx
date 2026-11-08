import { useTranslation } from "react-i18next";
import type {
  CompletionAnswer,
  GraduationResult,
  GraduationUseCases,
} from "../../../../modules/requirements/public.ts";
import { useCompletionAssessment } from "../../hooks/requirements/useCompletionAssessment.ts";
import { FormError } from "../StatusPanels.tsx";
import { GraduationResultView } from "./GraduationResultView.tsx";

export function CompletionAssessment({
  result,
  useCases,
  csrf,
  expire,
}: {
  result: GraduationResult;
  useCases: GraduationUseCases;
  csrf: string;
  expire: () => void;
}) {
  const { t } = useTranslation();
  const assessment = useCompletionAssessment(result, useCases, csrf, expire);
  const shown = assessment.checked ?? result;
  return (
    <>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void assessment.assess();
        }}
      >
        <fieldset disabled={assessment.busy}>
          <legend>{t("単位以外の修了条件（本人申告）")}</legend>
          <p>
            {t(
              "回答は判定履歴に保存されます。再読み込み後は再入力してください。",
            )}
          </p>
          {(result.completionConditions ?? []).map((condition) => (
            <div key={condition.code}>
              <label htmlFor={`completion-${condition.code}`}>
                {condition.name}
              </label>{" "}
              <select
                id={`completion-${condition.code}`}
                value={
                  assessment.answers.find((a) => a.code === condition.code)
                    ?.status ?? "unknown"
                }
                onChange={(event) =>
                  assessment.change(
                    condition.code,
                    event.target.value as CompletionAnswer["status"],
                  )
                }
              >
                <option value="unknown">{t("未確認")}</option>
                <option value="met">{t("達成")}</option>
                <option value="not_met">{t("未達成")}</option>
              </select>
            </div>
          ))}
          <button type="submit" className="primary-button">
            {assessment.busy ? t("判定中…") : t("回答を反映して判定")}
          </button>
        </fieldset>
        {assessment.error && <FormError>{assessment.error}</FormError>}
        {assessment.checked && (
          <p role="status">
            {t("本人申告を含む参考判定")}:{" "}
            {t(
              assessment.checked.result === "pass"
                ? "達成"
                : assessment.checked.result === "fail"
                  ? "未達成"
                  : "判定保留",
            )}
          </p>
        )}
      </form>
      <GraduationResultView result={shown} />
    </>
  );
}
