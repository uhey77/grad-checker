import { useState } from "react";
import type { CatalogCourse } from "../../modules/subjects/public.ts";
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
} from "../../modules/grades/public.ts";
import { ScrollTable } from "../ScrollTable";
import { NoMatchingSubjects } from "../subjects/NoMatchingSubjects";
import {
  ClassificationCell,
  CreditsCell,
  OfferingsCell,
  ProviderCell,
  SubjectNameCell,
  SubjectTypeBadge,
} from "../subjects/SubjectCells";
import { termLabels } from "../subjects/labels";
import { courseStatusLabels, gradeChoiceLabels } from "./labels";

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
  const label = `${course.name} 第${attempt.attemptNo}回`;
  // 再履修の前の回次は不合格だけを選べる。合格・未確定は最新回次にだけ置ける。
  const choices: GradeChoice[] = latest
    ? [...gradeCodes, "pending"]
    : [...failingGradeCodes];
  return (
    <div className="attempt" role="group" aria-label={label}>
      <span className="attempt-number">第{attempt.attemptNo}回</span>
      <select
        aria-label={`${label}の成績`}
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
        {only ? <option value="">未履修</option> : null}
        {choices.map((choice) => (
          <option key={choice} value={choice}>
            {gradeChoiceLabels[choice]}
          </option>
        ))}
      </select>
      <input
        aria-label={`${label}の履修年度（任意）`}
        type="number"
        inputMode="numeric"
        min={minAcademicYear}
        max={maxAcademicYear}
        placeholder="年度"
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
        aria-label={`${label}の履修学期（任意）`}
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
        <option value="">学期未入力</option>
        {Object.entries(termLabels).map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
      {latest && attempt.attemptNo > 1 ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => actions.removeLatest(course.courseId)}
        >
          第{attempt.attemptNo}回を削除
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
        note="非表示の科目の成績は保持されます。"
        resetFilters={resetFilters}
      />
    );
  return (
    <>
      {courses.length > pageSize && (
        <nav aria-label="成績一覧のページ">
          <button
            type="button"
            disabled={disabled || currentPage === 0}
            onClick={() => setPage(currentPage - 1)}
          >
            前の100件
          </button>
          <span role="status">
            {" "}
            {currentPage * pageSize + 1}〜
            {Math.min((currentPage + 1) * pageSize, courses.length)}件／
            {courses.length}件{" "}
          </span>
          <button
            type="button"
            disabled={
              disabled || (currentPage + 1) * pageSize >= courses.length
            }
            onClick={() => setPage(currentPage + 1)}
          >
            次の100件
          </button>
        </nav>
      )}
      <ScrollTable
        label="成績入力の科目一覧"
        caption="本人の成績入力"
        className="grade-table"
      >
        <thead>
          <tr>
            <th scope="col">科目名</th>
            <th scope="col">本人課程の区分・種別</th>
            <th scope="col">単位</th>
            <th scope="col">開講学期</th>
            <th scope="col">開講元・授業形態</th>
            <th scope="col">成績（回次・成績・履修年度・学期）</th>
            <th scope="col">修得状況</th>
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
                  emptyLabel="本人課程の科目表になし"
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
                        aria-label={`${course.name}の成績`}
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
                        <option value="">未履修</option>
                        {[...gradeCodes, "pending" as const].map((choice) => (
                          <option key={choice} value={choice}>
                            {gradeChoiceLabels[choice]}
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
                      再履修を追加
                    </button>
                  ) : null}
                </td>
                <td>
                  <span className={`badge status-${status}`}>
                    {courseStatusLabels[status]}
                  </span>
                  {changed ? <small>未保存の変更あり</small> : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </ScrollTable>
    </>
  );
}
