import { useTranslation } from "react-i18next";
import { useState } from "react";
import type { CatalogCourse } from "../../../../modules/subjects/public.ts";
import {
  attemptsOf,
  canAddRetake,
  courseStatus,
  failingGradeCodes,
  gradeCodes,
  maxAcademicYear,
  minAcademicYear,
  sameGrades,
  type GradeAttempt,
  type GradeChoice,
  type TermCode,
} from "../../../../modules/grades/public.ts";
import { ScrollTable } from "../ScrollTable.tsx";
import { NoMatchingSubjects } from "../subjects/NoMatchingSubjects.tsx";
import {
  ClassificationCell,
  CreditsCell,
  OfferingsCell,
  ProviderCell,
  SubjectNameCell,
  SubjectTypeBadge,
} from "../subjects/SubjectCells.tsx";
import { termLabels } from "../subjects/labels.ts";
import { courseStatusLabels, gradeChoiceLabels } from "./labels.ts";
interface Actions {
  choose: (
    courseId: string,
    attemptNo: number,
    choice: GradeChoice | "",
  ) => void;
  setPeriod: (
    courseId: string,
    attemptNo: number,
    year: number | null,
    term: TermCode | null,
  ) => void;
  addRetake: (courseId: string) => void;
  removeLatest: (courseId: string) => void;
}
function AttemptEditor({
  course,
  attempt,
  latest,
  only,
  disabled,
  actions,
}: {
  course: CatalogCourse;
  attempt: GradeAttempt;
  latest: boolean;
  only: boolean;
  disabled: boolean;
  actions: Actions;
}) {
  const { t } = useTranslation();
  const label = t("{{value0}} 第{{value1}}回", {
    value0: course.name,
    value1: attempt.attemptNo,
  });
  // 再履修の前の回次は不合格だけを選べる。合格・未確定は最新回次にだけ置ける。
  const choices: GradeChoice[] = latest
    ? [...gradeCodes, "pending"]
    : [...failingGradeCodes];
  return (
    <div className="attempt" role="group" aria-label={label}>
      <span className="attempt-number">
        {t("第{{value0}}回", { value0: attempt.attemptNo })}
      </span>
      <select
        aria-label={t("{{value0}}の成績", { value0: label })}
        value={attempt.gradeCode ?? "pending"}
        disabled={disabled}
        onChange={(event) =>
          actions.choose(
            course.courseId,
            attempt.attemptNo,
            event.target.value as GradeChoice | "",
          )
        }
      >
        {only ? <option value="">{t("未履修")}</option> : null}
        {choices.map((choice) => (
          <option key={choice} value={choice}>
            {t(gradeChoiceLabels[choice])}
          </option>
        ))}
      </select>
      <input
        aria-label={t("{{value0}}の履修年度（任意）", { value0: label })}
        type="number"
        inputMode="numeric"
        min={minAcademicYear}
        max={maxAcademicYear}
        placeholder={t("年度")}
        value={attempt.academicYear ?? ""}
        disabled={disabled}
        onChange={(event) =>
          actions.setPeriod(
            course.courseId,
            attempt.attemptNo,
            event.target.value === ""
              ? null
              : Number.parseInt(event.target.value, 10),
            attempt.termCode,
          )
        }
      />
      <select
        aria-label={t("{{value0}}の履修学期（任意）", { value0: label })}
        value={attempt.termCode ?? ""}
        disabled={disabled}
        onChange={(event) =>
          actions.setPeriod(
            course.courseId,
            attempt.attemptNo,
            attempt.academicYear,
            (event.target.value || null) as TermCode | null,
          )
        }
      >
        <option value="">{t("学期未入力")}</option>
        {Object.entries(termLabels).map(([value, text]) => (
          <option key={value} value={value}>
            {t(text)}
          </option>
        ))}
      </select>
      {latest && attempt.attemptNo > 1 ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => actions.removeLatest(course.courseId)}
        >
          {t("第{{value0}}回を削除", { value0: attempt.attemptNo })}
        </button>
      ) : null}
    </div>
  );
}
export function GradeTable({
  courses,
  draft,
  saved,
  disabled,
  resetFilters,
  ...actions
}: Actions & {
  courses: CatalogCourse[];
  draft: GradeAttempt[];
  saved: GradeAttempt[];
  disabled: boolean;
  resetFilters: () => void;
}) {
  const { t } = useTranslation();
  const [page, setPage] = useState(0);
  const pageSize = 100;
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil(courses.length / pageSize) - 1),
  );
  const visibleCourses = courses.slice(
    currentPage * pageSize,
    (currentPage + 1) * pageSize,
  );
  if (courses.length === 0)
    return (
      <NoMatchingSubjects
        note={t("非表示の科目の成績は保持されます。")}
        resetFilters={resetFilters}
      />
    );
  return (
    <>
      {courses.length > pageSize && (
        <nav aria-label={t("成績一覧のページ")}>
          <button
            type="button"
            disabled={disabled || currentPage === 0}
            onClick={() => setPage(currentPage - 1)}
          >
            {t("前の100件")}
          </button>
          <span role="status">
            {t(" {{value0}}〜{{value1}}件／{{value2}}件 ", {
              value0: currentPage * pageSize + 1,
              value1: Math.min((currentPage + 1) * pageSize, courses.length),
              value2: courses.length,
            })}
          </span>
          <button
            type="button"
            disabled={
              disabled || (currentPage + 1) * pageSize >= courses.length
            }
            onClick={() => setPage(currentPage + 1)}
          >
            {t("次の100件")}
          </button>
        </nav>
      )}
      <ScrollTable
        label={t("成績入力の科目一覧")}
        caption={t("本人の成績入力")}
        className="grade-table"
      >
        <thead>
          <tr>
            <th scope="col">{t("科目名")}</th>
            <th scope="col">{t("本人課程の区分・種別")}</th>
            <th scope="col">{t("単位")}</th>
            <th scope="col">{t("開講学期")}</th>
            <th scope="col">{t("開講元・授業形態")}</th>
            <th scope="col">{t("成績（回次・成績・履修年度・学期）")}</th>
            <th scope="col">{t("修得状況")}</th>
          </tr>
        </thead>
        <tbody>
          {visibleCourses.map((course) => {
            const attempts = attemptsOf(draft, course.courseId);
            const status = courseStatus(attempts);
            const changed = !sameGrades(
              attempts,
              attemptsOf(saved, course.courseId),
            );
            const placement = course.placement;
            return (
              <tr
                key={course.courseId}
                className={status === "earned" ? "earned-row" : undefined}
              >
                <SubjectNameCell name={course.name} code={course.code} />
                <ClassificationCell
                  path={placement?.classificationPath ?? []}
                  emptyLabel={t("本人課程の科目表になし")}
                >
                  {placement ? (
                    <SubjectTypeBadge type={placement.courseType} />
                  ) : null}
                </ClassificationCell>
                <CreditsCell credits={course.credits} />
                <OfferingsCell offerings={course.offerings} />
                <ProviderCell
                  facultyName={course.offeringFacultyName}
                  departmentName={course.offeringDepartmentName}
                  specializationName={course.offeringSpecializationName}
                  teachingTypeLabel={course.teachingTypeLabel}
                />
                <td className="grade-cell">
                  {attempts.length === 0 ? (
                    <div className="attempt">
                      <select
                        aria-label={t("{{value0}}の成績", {
                          value0: course.name,
                        })}
                        value=""
                        disabled={disabled}
                        onChange={(event) =>
                          actions.choose(
                            course.courseId,
                            1,
                            event.target.value as GradeChoice,
                          )
                        }
                      >
                        <option value="">{t("未履修")}</option>
                        {[...gradeCodes, "pending" as const].map((choice) => (
                          <option key={choice} value={choice}>
                            {t(gradeChoiceLabels[choice])}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    attempts.map((attempt, index) => (
                      <AttemptEditor
                        key={attempt.attemptNo}
                        course={course}
                        attempt={attempt}
                        latest={index === attempts.length - 1}
                        only={attempts.length === 1}
                        disabled={disabled}
                        actions={actions}
                      />
                    ))
                  )}
                  {canAddRetake(attempts) ? (
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => actions.addRetake(course.courseId)}
                    >
                      {t("再履修を追加")}
                    </button>
                  ) : null}
                </td>
                <td>
                  <span className={`badge status-${status}`}>
                    {t(courseStatusLabels[status])}
                  </span>
                  {changed ? <small>{t("未保存の変更あり")}</small> : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </ScrollTable>
    </>
  );
}
