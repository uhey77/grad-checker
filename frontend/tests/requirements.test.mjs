import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const load = (path) =>
  import(pathToFileURL(join(process.env.SUBJECT_TEST_BUILD_DIRECTORY, path)));
const { HttpGraduationRepository } = await load(
  "modules/requirements/infrastructure/HttpGraduationRepository.js",
);
const { GraduationUseCases } = await load(
  "modules/requirements/application/GraduationUseCases.js",
);
const { toGraduationResult } = await load(
  "modules/requirements/infrastructure/mappers.js",
);

const summary = {
  required_credits: 10,
  earned_credits: 8,
  credited_credits: 8,
  shortage: 2,
  result: "fail",
};
function fixture() {
  return {
    result: "fail",
    data_revision: 2,
    evaluated_at: "2026-10-16T00:00:00Z",
    curriculum: {
      id: "curriculum",
      name: "テスト課程",
      revision: 1,
      verification_status: "verified",
      source_document: "テスト便覧",
      source_pages: "1",
    },
    total: { ...summary },
    requirements: [
      {
        ...summary,
        id: "total",
        code: "total",
        name: "総単位",
        kind: "total",
        parent_id: null,
        classification_id: null,
      },
    ],
    missing_required_courses: [
      { course_id: "course", name: "必修科目", credits: 2 },
    ],
    allocations: [{ requirement_id: "total", transferred_credits: 2 }],
  };
}

test("判定は本人の保存済みデータをGETし、Cookie・キャンセル・キャッシュ禁止を維持する", async (context) => {
  const calls = [];
  context.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push({ url, options });
    return Response.json(fixture());
  });
  const controller = new AbortController();
  const service = new GraduationUseCases(new HttpGraduationRepository("/api"));
  const result = await service.evaluate(controller.signal);
  assert.equal(result.result, "fail");
  assert.equal(result.total.shortage, 2);
  assert.equal(result.dataRevision, 2);
  assert.equal(result.curriculum.sourceDocument, "テスト便覧");
  assert.equal(result.missingRequiredCourses[0].courseId, "course");
  assert.equal(result.allocations[0].transferredCredits, 2);
  assert.equal(calls.length, 1);
  const { url, options } = calls[0];
  assert.equal(url, "/api/me/graduation-requirements");
  assert.equal(options.method, "GET");
  assert.equal(options.body, undefined);
  assert.equal(options.credentials, "same-origin");
  assert.equal(options.cache, "no-store");
  assert.equal(options.signal, controller.signal);
});

test("未確認設定・認証・通信失敗を未達成へ読み替えず理由を保持する", async (context) => {
  const repo = new HttpGraduationRepository("/api");
  const fetch = context.mock.method(globalThis, "fetch", async () =>
    Response.json({ detail: "適用年度が未確認です" }, { status: 409 }),
  );
  await assert.rejects(
    repo.evaluate(),
    (error) => error.status === 409 && error.message === "適用年度が未確認です",
  );
  fetch.mock.mockImplementation(async () =>
    Response.json({ detail: "ログインしてください" }, { status: 401 }),
  );
  await assert.rejects(repo.evaluate(), (error) => error.status === 401);
  fetch.mock.mockImplementation(async () => {
    throw new TypeError("offline");
  });
  await assert.rejects(repo.evaluate(), (error) => error.status === 0);
  const cancellation = new DOMException("Aborted", "AbortError");
  fetch.mock.mockImplementation(async () => {
    throw cancellation;
  });
  await assert.rejects(repo.evaluate(), (error) => error === cancellation);
});

test("不正・欠落・未確認の成功応答を結果画面へ渡さない", () => {
  const changes = [
    (data) => (data.result = "unknown"),
    (data) => (data.total.shortage = -1),
    (data) => (data.total.earned_credits = 1.5),
    (data) => (data.data_revision = null),
    (data) => (data.curriculum.verification_status = "unverified"),
    (data) => (data.evaluated_at = "invalid"),
    (data) => (data.requirements = []),
    (data) => data.requirements.push(data.requirements[0]),
    (data) => (data.requirements[0].kind = "unknown"),
    (data) => (data.requirements[0].parent_id = undefined),
    (data) => (data.missing_required_courses = null),
    (data) => (data.missing_required_courses[0].credits = 0),
    (data) => (data.allocations = null),
  ];
  for (const change of changes) {
    const data = fixture();
    change(data);
    assert.throws(
      () => toGraduationResult(data),
      (error) => error.status === 502,
    );
  }
});
