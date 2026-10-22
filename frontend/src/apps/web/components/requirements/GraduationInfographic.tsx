import { Trans, useTranslation } from "react-i18next";
import { useEntranceProgress } from "../../hooks/useEntranceProgress.ts";
import type {
  GraduationResult,
  RequirementResult,
} from "../../../../modules/requirements/public.ts";

function fraction(credited: number, required: number) {
  return required === 0 ? 1 : Math.min(credited / required, 1);
}
export function GraduationInfographic({
  result,
  categories,
}: {
  result: Pick<GraduationResult, "total" | "result">;
  categories: RequirementResult[];
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
        <h3>{t("総単位の充足率")}</h3>
        <div
          className="credit-orbit"
          role="img"
          aria-label={t(
            "総単位の充足率 {{value0}}%。算入{{value1}}単位、必要{{value2}}単位",
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
        <p className="credit-orbit-caption">
          {total.shortage > 0 ? (
            <Trans
              i18nKey="総単位の不足は <strong>{{credits}}単位</strong>"
              values={{ credits: total.shortage }}
              components={{ strong: <strong /> }}
            />
          ) : (
            <strong>{t("総単位の条件を満たしています")}</strong>
          )}
        </p>
      </div>
      <div className="category-progress-panel">
        <h3>{t("区分別の単位")}</h3>
        <p className="category-progress-help">
          {t("各区分に算入される単位を表示しています。")}
        </p>
        <div className="category-progress-list">
          {categories.map((row, index) => {
            const delay = Math.min(index, 4) * 0.1;
            const reveal = Math.max(0, (progress - delay) / (1 - delay));
            return (
              <div className="category-progress" key={row.id}>
                <div className="category-progress-heading">
                  <span>{row.name}</span>
                  <span className={`category-progress-status ${row.result}`}>
                    {row.result === "pass"
                      ? t("合計達成")
                      : t("あと{{value0}}単位", { value0: row.shortage })}
                  </span>
                </div>
                <div
                  className="category-progress-track"
                  role="meter"
                  aria-label={row.name}
                  aria-valuemin={0}
                  aria-valuemax={Math.max(1, row.requiredCredits)}
                  aria-valuenow={Math.min(
                    row.creditedCredits,
                    row.requiredCredits,
                  )}
                  aria-valuetext={t(
                    "算入{{value0}}単位、必要{{value1}}単位、不足{{value2}}単位",
                    {
                      value0: row.creditedCredits,
                      value1: row.requiredCredits,
                      value2: row.shortage,
                    },
                  )}
                >
                  <span
                    className={`category-progress-fill tone-${index % 3}`}
                    style={{
                      transform: `scaleX(${fraction(row.creditedCredits, row.requiredCredits) * reveal})`,
                    }}
                  />
                </div>
                <p className="category-progress-count">
                  <strong>{row.creditedCredits}</strong>
                  {t(" / {{value0}} 単位", { value0: row.requiredCredits })}
                </p>
              </div>
            );
          })}
        </div>
        {total.result === "pass" && result.result === "fail" && (
          <p className="category-progress-footnote">
            {t(
              "総単位は満たしていますが、必修・内訳などに未達成の条件が残っています。",
            )}
          </p>
        )}
      </div>
    </section>
  );
}
