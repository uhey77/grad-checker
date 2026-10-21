import assert from "node:assert/strict";

import test from "node:test";

import { pathToFileURL } from "node:url";

import { join } from "node:path";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;

const load = (path) => import(pathToFileURL(join(directory, path)));

const draft = await load("modules/grades/application/services/gradeDraft.js");

const { gradeDraftProblemMessage } = await load(
  "apps/web/hooks/grades/errors.js",
);

const { courseStatus, isValidAttemptSequence } = await load(
  "modules/grades/domain/services/attempts.js",
);

const attempt = (
  course,
  number = 1,
  code = "A",
  year = 2026,
  term = "first",
) => ({
  courseId: course,
  attemptNo: number,
  resultStatus: code ? "finalized" : "pending",
  gradeCode: code,
  academicYear: year,
  termCode: term,
});

test("成績の編集は合格・未確定の後に再履修を追加せず、全集合を保持する", () => {
  let grades = [attempt("other", 1, "B")];
  grades = draft.chooseGrade(grades, "c1", 1, "D");
  assert.deepEqual(draft.attemptsOf(grades, "c1"), [
    attempt("c1", 1, "D", null, null),
  ]);
  assert.equal(courseStatus(draft.attemptsOf(grades, "c1")), "failed");
  grades = draft.addRetake(grades, "c1");
  assert.equal(draft.attemptsOf(grades, "c1")[1].resultStatus, "pending");
  assert.equal(courseStatus(draft.attemptsOf(grades, "c1")), "pending");
  // 未確定の後には追加できない。
  assert.deepEqual(draft.addRetake(grades, "c1"), grades);
  grades = draft.chooseGrade(grades, "c1", 2, "A");
  assert.equal(courseStatus(draft.attemptsOf(grades, "c1")), "earned");
  assert.equal(draft.canAddRetake(draft.attemptsOf(grades, "c1")), false);
  grades = draft.setAttemptPeriod(grades, "c1", 2, 2026, "second");
  assert.deepEqual(
    draft.attemptsOf(grades, "c1")[1],
    attempt("c1", 2, "A", 2026, "second"),
  );
  assert.equal(draft.draftProblem(grades), null);
  assert.equal(
    draft.draftProblem(draft.chooseGrade(grades, "c1", 1, "A")),
    "invalid_attempt_sequence",
  );
  assert.equal(
    draft.draftProblem(draft.setAttemptPeriod(grades, "c1", 1, 1800, null)),
    "invalid_academic_year",
  );
  grades = draft.removeLatestAttempt(grades, "c1");
  assert.equal(draft.attemptsOf(grades, "c1").length, 1);
  // 2回目以降がある科目は""で未履修へ戻さない。1回だけなら記録を消す。
  grades = draft.chooseGrade(grades, "c1", 1, "");
  assert.deepEqual(grades, [attempt("other", 1, "B")]);
  assert.ok(
    draft.sameGrades(
      [attempt("a"), attempt("b")],
      [attempt("b"), attempt("a")],
    ),
  );
  assert.ok(!draft.sameGrades([attempt("a")], [attempt("a", 1, "B")]));
});

test("修得状況と履修年度・学期で絞り込み、年度と学期は同じ回次で一致させる", () => {
  const attempts = [
    attempt("c", 1, "D", 2025, "first"),
    attempt("c", 2, "A", 2026, "second"),
  ];
  const filters = { ...draft.emptyGradeFilters };
  assert.ok(
    draft.matchesGradeFilters(attempts, { ...filters, status: "earned" }),
  );
  assert.ok(
    !draft.matchesGradeFilters(attempts, { ...filters, status: "failed" }),
  );
  assert.ok(
    draft.matchesGradeFilters(attempts, {
      ...filters,
      year: "2025",
      term: "first",
    }),
  );
  assert.ok(
    !draft.matchesGradeFilters(attempts, {
      ...filters,
      year: "2025",
      term: "second",
    }),
  );
  assert.ok(draft.matchesGradeFilters([], { ...filters, status: "not-taken" }));
  assert.ok(!draft.matchesGradeFilters([], { ...filters, year: "2025" }));
  assert.deepEqual(
    draft.takenYears([...attempts, attempt("d", 1, "A", null)]),
    [2026, 2025],
  );
});

test("成績のDomainは連番・再履修を検証し、画面が入力エラーを日本語へ変換する", () => {
  const valid = [attempt("c", 2, "A"), attempt("c", 1, "D")];
  assert.ok(isValidAttemptSequence(valid));
  assert.equal(valid[0].attemptNo, 2);
  for (const invalid of [
    [attempt("c", 2, "A")],
    [attempt("c", 1, "D"), attempt("c", 1, "A")],
    [attempt("c", 1, "D"), attempt("c", 3, "A")],
    [attempt("c", 1, "A"), attempt("c", 2, "D")],
    [attempt("c", 1, null), attempt("c", 2, "A")],
  ])
    assert.equal(isValidAttemptSequence(invalid), false);
  assert.equal(gradeDraftProblemMessage(null), null);
  assert.equal(
    gradeDraftProblemMessage("invalid_academic_year"),
    "履修年度は1900〜2100の整数で入力してください。",
  );
  assert.equal(
    gradeDraftProblemMessage("invalid_attempt_sequence"),
    "再履修の前の回次は不合格（D・X）にしてください。",
  );
});
