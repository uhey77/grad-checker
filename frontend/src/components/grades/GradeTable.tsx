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
import { offeringLabels, subjectTypeLabels } from "../subjects/labels";
import { courseStatusLabels, gradeChoiceLabels, termLabels } from "./labels";

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
  if (courses.length === 0) {
    return (
      <div className="empty" role="status">
        <strong>条件に一致する科目がありません</strong>
        <p>
          検索語や絞り込み条件を変更してください。非表示の科目の成績は保持されます。
        </p>
        <button type="button" onClick={resetFilters}>
          すべての条件をクリア
        </button>
      </div>
    );
  }
  return (
    <>
      <p className="table-hint">一覧は左右にスクロールできます。</p>
      <div
        className="table-scroll"
        tabIndex={0}
        role="region"
        aria-label="成績入力の科目一覧。狭い画面では横にスクロールできます"
      >
        <table className="grade-table">
          <caption className="sr-only">本人の成績入力</caption>
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
            {courses.map((course) => {
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
                  <th scope="row">
                    {course.name}
                    <small>{course.code}</small>
                  </th>
                  <td>
                    {placement ? (
                      <>
                        <span>
                          {placement.classificationPath
                            .map((item) => item.name)
                            .join(" / ")}
                        </span>
                        <span className={`badge ${placement.courseType}`}>
                          {subjectTypeLabels[placement.courseType]}
                        </span>
                      </>
                    ) : (
                      <span>本人課程の科目表になし</span>
                    )}
                  </td>
                  <td className="credits">{course.credits}</td>
                  <td className="offerings">
                    {offeringLabels(course.offerings).join("・") || "記載なし"}
                  </td>
                  <td>
                    {course.offeringFacultyName}
                    <small>
                      {[
                        course.offeringDepartmentName,
                        course.offeringSpecializationName,
                        course.teachingTypeLabel,
                      ]
                        .filter(Boolean)
                        .join("・")}
                    </small>
                  </td>
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
        </table>
      </div>
    </>
  );
}
