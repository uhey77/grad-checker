import { useEntranceProgress } from "../../hooks/useEntranceProgress";
import type {
  GraduationResult,
  RequirementResult,
} from "../../modules/requirements/public.ts";

const percent = new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 1 });

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
  const progress = useEntranceProgress();
  const total = result.total;
  const ratio = fraction(total.creditedCredits, total.requiredCredits);

  return (
    <section className="graduation-infographic" aria-label="単位の進捗グラフ">
      <div className="credit-orbit-panel">
        <h3>総単位の充足率</h3>
        <div
          className="credit-orbit"
          role="img"
          aria-label={`総単位の充足率 ${percent.format(ratio * 100)}%。算入${total.creditedCredits}単位、必要${total.requiredCredits}単位`}
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
              <span> / {total.requiredCredits} 単位</span>
            </span>
          </div>
        </div>
        <p className="credit-orbit-caption">
          {total.shortage > 0 ? (
            <>
              総単位の不足は <strong>{total.shortage}単位</strong>
            </>
          ) : (
            <strong>総単位の条件を満たしています</strong>
          )}
        </p>
      </div>
      <div className="category-progress-panel">
        <h3>区分別の単位</h3>
        <p className="category-progress-help">
          各区分に算入される単位を表示しています。
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
                      ? "合計達成"
                      : `あと${row.shortage}単位`}
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
                  aria-valuetext={`算入${row.creditedCredits}単位、必要${row.requiredCredits}単位、不足${row.shortage}単位`}
                >
                  <span
                    className={`category-progress-fill tone-${index % 3}`}
                    style={{
                      transform: `scaleX(${fraction(row.creditedCredits, row.requiredCredits) * reveal})`,
                    }}
                  />
                </div>
                <p className="category-progress-count">
                  <strong>{row.creditedCredits}</strong> / {row.requiredCredits}{" "}
                  単位
                </p>
              </div>
            );
          })}
        </div>
        {total.result === "pass" && result.result === "fail" && (
          <p className="category-progress-footnote">
            総単位は満たしていますが、必修・内訳などに未達成の条件が残っています。
          </p>
        )}
      </div>
    </section>
  );
}
