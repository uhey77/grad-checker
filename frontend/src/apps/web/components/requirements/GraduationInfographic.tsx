import { useTranslation } from "react-i18next";
import { useEntranceProgress } from "../../hooks/useEntranceProgress.ts";
import type { GraduationResult } from "../../../../modules/requirements/public.ts";

function fraction(credited: number, required: number) {
  return required === 0 ? 1 : Math.min(credited / required, 1);
}
export function GraduationInfographic({
  result,
}: {
  result: Pick<GraduationResult, "total" | "result">;
}) {
  const { t, i18n } = useTranslation();
  const percent = new Intl.NumberFormat(i18n.resolvedLanguage, {
    maximumFractionDigits: 1,
  });
  const progress = useEntranceProgress();
  const total = result.total;
  const ratio = fraction(total.creditedCredits, total.requiredCredits);
  return (
    <section
      className="graduation-infographic"
      aria-label={t("単位の進捗グラフ")}
    >
      <div className="credit-orbit-panel">
        <h3>{t("必要単位の進捗")}</h3>
        <div
          className="credit-orbit"
          role="img"
          aria-label={t(
            "必要単位の進捗 {{value0}}%。算入{{value1}}単位、必要{{value2}}単位",
            {
              value0: percent.format(ratio * 100),
              value1: total.creditedCredits,
              value2: total.requiredCredits,
            },
          )}
        >
          <svg viewBox="0 0 200 200" aria-hidden="true" focusable="false">
            <circle className="credit-orbit-track" cx="100" cy="100" r="83" />
            <circle
              className="credit-orbit-fill"
              cx="100"
              cy="100"
              r="83"
              pathLength="100"
              strokeDasharray={`${ratio * progress * 100} 100`}
              strokeLinecap={ratio * progress > 0 ? "round" : "butt"}
            />
          </svg>
          <div className="credit-orbit-value" aria-hidden="true">
            <strong>
              {percent.format(ratio * progress * 100)}
              <small>%</small>
            </strong>
            <span>
              <b>{Math.round(total.creditedCredits * progress)}</b>
              <span>
                {t(" / {{value0}} 単位", { value0: total.requiredCredits })}
              </span>
            </span>
          </div>
        </div>
        {total.shortage === 0 && (
          <p className="credit-orbit-caption">
            <strong>{t("総単位の条件を満たしています")}</strong>
          </p>
        )}
        {total.result === "pass" && result.result === "fail" && (
          <p className="credit-orbit-footnote">
            {t(
              "総単位は満たしていますが、必修・内訳などに未達成の条件が残っています。",
            )}
          </p>
        )}
      </div>
    </section>
  );
}
