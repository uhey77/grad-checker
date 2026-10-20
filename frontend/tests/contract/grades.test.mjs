import assert from "node:assert/strict";

import test from "node:test";

import { pathToFileURL } from "node:url";

import { join } from "node:path";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;

const load = (path) => import(pathToFileURL(join(directory, path)));

const { HttpGradeRepository } = await load(
  "modules/grades/infrastructure/external_services/HttpGradeRepository.js",
);

const { createGradesModule } = await load("modules/grades/composition.js");

const { toStudentGrades } = await load(
  "modules/grades/infrastructure/external_services/schemas/mappers.js",
);

const dto = (course, number = 1, code = "A", year = 2026, term = "first") => ({
  course_id: course,
  attempt_no: number,
  result_status: code ? "finalized" : "pending",
  grade_code: code,
  academic_year: year,
  term_code: term,
});

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

test("成績APIのDTO変換・全集合のPUT・Cookie・CSRF・更新版の契約", async (context) => {
  const requests = [];
  const controller = new AbortController();
  context.mock.method(globalThis, "fetch", async (url, options) => {
    requests.push({ url, options });
    return Response.json(
      options.method === "PUT"
        ? {
            ...JSON.parse(options.body),
            data_revision: 4,
            expected_revision: undefined,
          }
        : {
            grades: [dto("c1", 1, "D"), dto("c1", 2, null, null, null)],
            data_revision: 3,
          },
    );
  });
  const useCases = createGradesModule("/api");
  const saved = await useCases.getGrades.execute(controller.signal);
  assert.equal(saved.dataRevision, 3);
  assert.deepEqual(saved.grades[1], attempt("c1", 2, null, null, null));
  const result = await useCases.saveGrades.execute(
    { expectedRevision: 3, grades: [attempt("c2", 1, "X", null, "second")] },
    "csrf",
    controller.signal,
  );
  assert.equal(result.dataRevision, 4);
  const put = requests.at(-1);
  assert.equal(put.url, "/api/me/grades");
  assert.equal(put.options.method, "PUT");
  assert.equal(put.options.headers["X-CSRF-Token"], "csrf");
  assert.deepEqual(JSON.parse(put.options.body), {
    expected_revision: 3,
    grades: [dto("c2", 1, "X", null, "second")],
  });
  for (const { url, options } of requests) {
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    assert.equal(options.signal, controller.signal);
    assert.ok(!url.includes("student_id"));
  }
});

test("成績の取得失敗は状態とdetailを保持し、キャンセルは変換しない", async (context) => {
  const repository = new HttpGradeRepository("/api");
  const fetch = context.mock.method(globalThis, "fetch", async () =>
    Response.json({ detail: "再取得してください" }, { status: 409 }),
  );
  await assert.rejects(
    repository.saveGrades({ expectedRevision: 0, grades: [] }, "csrf"),
    (error) => error.status === 409 && error.message === "再取得してください",
  );
  fetch.mock.mockImplementation(async () => {
    throw new TypeError("network");
  });
  await assert.rejects(repository.getGrades(), (error) => error.status === 0);
  const controller = new AbortController();
  controller.abort();
  const reason = new DOMException("Aborted", "AbortError");
  fetch.mock.mockImplementation(async () => {
    throw reason;
  });
  await assert.rejects(
    repository.getGrades(controller.signal),
    (error) => error === reason,
  );
});

test("不正な成績応答を確定値へ読み替えない", () => {
  for (const invalid of [
    null,
    { grades: null, data_revision: 0 },
    { grades: [], data_revision: -1 },
    { grades: [{ ...dto("c"), grade_code: null }], data_revision: 0 },
    { grades: [{ ...dto("c"), result_status: "pending" }], data_revision: 0 },
    { grades: [{ ...dto("c"), grade_code: "R" }], data_revision: 0 },
    { grades: [{ ...dto("c"), term_code: "summer" }], data_revision: 0 },
    { grades: [{ ...dto("c"), attempt_no: 0 }], data_revision: 0 },
  ]) {
    assert.throws(
      () => toStudentGrades(invalid),
      (error) => error.status === 502,
    );
  }
});
