import { useTranslation } from "react-i18next";
import type {
  CourseRecommendation,
  GraduationResult,
  RequirementResult,
} from "../../../../modules/requirements/public.ts";
import { requirementCategoryName } from "./RequirementMatrix.tsx";

function CourseList({
  courses,
  recommendations,
  requirementId,
}: {
  courses: { courseId: string; name: string; credits: number }[];
  recommendations?: CourseRecommendation[] | null;
  requirementId?: string;
}) {
  const { t } = useTranslation();
  return (
    <ul className="shortage-course-list">
      {courses.map((course) => {
        const recommendation = recommendations?.find(
          (row) => row.courseId === course.courseId,
        );
        return (
          <li key={course.courseId}>
            <div className="shortage-course-info">
              <span>{course.name}</span>
              {recommendation && (
                <div className="shortage-course-meta">
                  {requirementId &&
                    recommendation.contributions
                      .filter(
                        (reason) => reason.requirementId === requirementId,
                      )
                      .map((reason) => (
                        <span key={reason.requirementId}>{reason.reason}</span>
                      ))}
                </div>
              )}
            </div>
            <span className="shortage-course-credits">
              {t("{{value0}}単位", { value0: course.credits })}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ShortageCondition({
  condition,
  recommendations,
  nested = false,
  collapsible = false,
}: {
  condition: RequirementResult;
  recommendations: GraduationResult["recommendations"];
  nested?: boolean;
  collapsible?: boolean;
}) {
  const { t } = useTranslation();
  const candidates = recommendations?.filter((course) =>
    course.contributions.some(
      (reason) => reason.requirementId === condition.id,
    ),
  );
  return (
    <div
      className={
        nested ? "shortage-condition shortage-subminimum" : "shortage-condition"
      }
    >
      <strong>
        {nested ? requirementCategoryName(condition) : condition.name}
      </strong>
      {candidates === undefined ? (
        <p>{t("この履歴にはおすすめ科目が保存されていません。")}</p>
      ) : candidates.length ? (
        collapsible ? (
          <details className="shortage-candidates">
            <summary
              aria-label={t("{{value0}}の候補を見る", {
                value0: condition.name,
              })}
            >
              {t("候補を見る")}
            </summary>
            <CourseList
              courses={candidates}
              recommendations={recommendations}
              requirementId={condition.id}
            />
          </details>
        ) : (
          <CourseList
            courses={candidates}
            recommendations={recommendations}
            requirementId={condition.id}
          />
        )
      ) : (
        <p>{t("この条件の候補は確認できていません。")}</p>
      )}
    </div>
  );
}

export function ShortageCourses({ result }: { result: GraduationResult }) {
  const { t } = useTranslation();
  const requiredConditions = result.requirements.filter(
    (condition) =>
      condition.kind === "required_courses" &&
      condition.classificationId !== null,
  );
  const groups = new Map<
    string,
    { name: string; courses: GraduationResult["missingRequiredCourses"] }
  >();
  const unclassified: GraduationResult["missingRequiredCourses"] = [];
  for (const course of result.missingRequiredCourses) {
    const matches = requiredConditions.filter(
      (condition) => condition.classificationId === course.classificationId,
    );
    const names = new Set(matches.map(requirementCategoryName));
    if (course.classificationId === null || names.size !== 1) {
      unclassified.push(course);
      continue;
    }
    const group = groups.get(course.classificationId) ?? {
      name: [...names][0],
      courses: [],
    };
    group.courses.push(course);
    groups.set(course.classificationId, group);
  }
  const kinds = [
    { kind: "selective_group", label: "選択必修" },
    { kind: "elective_total", label: "選択" },
  ] as const;
  const selectiveGroups = result.requirements.filter(
    (condition) => condition.kind === "selective_group",
  );
  const subminimums = result.requirements.filter(
    (condition) => condition.kind === "subminimum" && condition.shortage > 0,
  );
  const orphanSubminimums = subminimums.filter(
    (condition) =>
      !selectiveGroups.some((parent) => parent.id === condition.parentId),
  );
  const visibleConditionIds = new Set(
    result.requirements
      .filter(
        (condition) =>
          (condition.kind === "selective_group" ||
            condition.kind === "elective_total" ||
            condition.kind === "subminimum") &&
          condition.shortage > 0,
      )
      .map((condition) => condition.id),
  );
  const requiredIds = new Set(
    result.missingRequiredCourses.map((course) => course.courseId),
  );
  const totalCondition = result.requirements.find(
    (condition) => condition.kind === "total" && condition.shortage > 0,
  );
  const otherCandidates = totalCondition
    ? (result.recommendations?.filter(
        (course) =>
          !requiredIds.has(course.courseId) &&
          course.contributions.some(
            (reason) => reason.requirementId === totalCondition.id,
          ) &&
          !course.contributions.some((reason) =>
            visibleConditionIds.has(reason.requirementId),
          ),
      ) ?? [])
    : [];

  return (
    <section className="shortage-courses" aria-label={t("不足単位と履修候補")}>
      <h3>{t("不足単位と履修候補")}</h3>
      <div className="shortage-group">
        <h4>{t("必修")}</h4>
        {result.missingRequiredCourses.length ? (
          <>
            <p>{t("次の必修科目を修得する必要があります。")}</p>
            <div className="shortage-category-grid">
              {[...groups.entries()].map(([id, group]) => (
                <section className="shortage-category" key={id}>
                  <h5>{group.name}</h5>
                  <CourseList
                    courses={group.courses}
                    recommendations={result.recommendations}
                  />
                </section>
              ))}
              {unclassified.length > 0 && (
                <section className="shortage-category">
                  <h5>{t("区分を確認できない必修科目")}</h5>
                  <CourseList
                    courses={unclassified}
                    recommendations={result.recommendations}
                  />
                </section>
              )}
            </div>
          </>
        ) : (
          <p>{t("未修得の必修科目はありません。")}</p>
        )}
      </div>
      {kinds.map(({ kind, label }) => {
        const conditions = result.requirements.filter(
          (condition) =>
            condition.kind === kind &&
            (condition.shortage > 0 ||
              (kind === "selective_group" &&
                subminimums.some((row) => row.parentId === condition.id))),
        );
        if (
          !conditions.length &&
          !(kind === "selective_group" && orphanSubminimums.length)
        )
          return null;
        return (
          <div key={kind} className="shortage-group">
            <h4>{t(label)}</h4>
            {conditions.map((condition) => (
              <div key={condition.id} className="shortage-condition">
                {condition.shortage > 0 ? (
                  <ShortageCondition
                    condition={condition}
                    recommendations={result.recommendations}
                    collapsible={
                      kind === "selective_group" || kind === "elective_total"
                    }
                  />
                ) : (
                  <strong>{condition.name}</strong>
                )}
                {kind === "selective_group" &&
                  subminimums
                    .filter((row) => row.parentId === condition.id)
                    .map((row) => (
                      <ShortageCondition
                        key={row.id}
                        condition={row}
                        recommendations={result.recommendations}
                        nested
                        collapsible
                      />
                    ))}
              </div>
            ))}
            {kind === "selective_group" &&
              orphanSubminimums.map((row) => (
                <ShortageCondition
                  key={row.id}
                  condition={row}
                  recommendations={result.recommendations}
                  nested
                  collapsible
                />
              ))}
          </div>
        );
      })}
      {otherCandidates.length > 0 && totalCondition && (
        <div className="shortage-group">
          <h4>{t("その他の履修候補")}</h4>
          <p>{t("総単位の不足を補える候補です。")}</p>
          <details className="shortage-candidates">
            <summary>{t("候補を見る")}</summary>
            <CourseList
              courses={otherCandidates}
              recommendations={result.recommendations}
              requirementId={totalCondition.id}
            />
          </details>
        </div>
      )}
    </section>
  );
}
