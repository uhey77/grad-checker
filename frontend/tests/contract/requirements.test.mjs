import assert from "node:assert/strict";

import test from "node:test";

import { pathToFileURL } from "node:url";

import { join } from "node:path";

const load = (path) =>
  import(pathToFileURL(join(process.env.SUBJECT_TEST_BUILD_DIRECTORY, path)));

const { HttpGraduationRepository } = await load(
  "modules/requirements/infrastructure/external_services/HttpGraduationRepository.js",
);

const { createRequirementsModule } = await load(
  "modules/requirements/composition.js",
);

const { toGraduationResult, toCheckPage, toSavedCheck } = await load(
  "modules/requirements/infrastructure/external_services/schemas/mappers.js",
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
    rule_revisions: {},
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
    warnings: [],
    external_allocations: [],
    recommendations: [],
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

function recommendation() {
  return {
    course_id: "candidate",
    name: "候補科目",
    credits: 2,
    status: "pending",
    is_required: true,
    offerings: [
      {
        course_id: "candidate",
        term_code: "first",
        semester_order: 1,
        academic_year: null,
        source_note: "便覧の注記",
      },
    ],
    contributions: [
      {
        requirement_id: "total",
        code: "T01",
        name: "総単位",
        shortage_reduction: 2,
        reason: "総単位の不足を2単位減らせる候補です。",
      },
    ],
  };
}

const checkId = "00000000-0000-4000-8000-000000000001";

function savedCheck() {
  const result = fixture();
  result.courses = [{ course_id: "course", name: "必修科目" }];
  return {
    id: checkId,
    created_at: "2026-10-16T00:00:00Z",
    input: {
      program_id: "program",
      curriculum_id: "curriculum",
      data_revision: 2,
      grades: [
        {
          course_id: "course",
          attempt_no: 1,
          result_status: "finalized",
          grade_code: "D",
          academic_year: 2026,
          term_code: "first",
        },
        {
          course_id: "removed",
          attempt_no: 1,
          result_status: "pending",
          grade_code: null,
          academic_year: null,
          term_code: null,
        },
      ],
    },
    result,
  };
}

function checkPage() {
  return {
    checks: [
      {
        id: checkId,
        created_at: "2026-10-16T00:00:00Z",
        data_revision: 2,
        result: "fail",
        curriculum: {
          id: "curriculum",
          code: "cs",
          name: "当時の課程",
          revision: 3,
        },
        total: { ...summary },
      },
    ],
    limit: 20,
    offset: 20,
    total_count: 21,
  };
}

function dashboardFixture() {
  const result = fixture();
  return {
    result: result.result,
    data_revision: result.data_revision,
    rule_revisions: result.rule_revisions,
    evaluated_at: result.evaluated_at,
    curriculum: result.curriculum,
    curriculum_revision: result.curriculum.revision,
    grade_count: 3,
    total: result.total,
    categories: [{ ...result.requirements[0], kind: "classification_total" }],
    warnings: result.warnings,
  };
}

test("推薦の順序・状態・開講期・条件コードと保存済みの理由を保持する", () => {
  const data = fixture();
  data.recommendations = [
    recommendation(),
    { ...recommendation(), course_id: "second", status: "not_taken" },
  ];
  const result = toGraduationResult(data);
  assert.deepEqual(
    result.recommendations.map((r) => r.courseId),
    ["candidate", "second"],
  );
  const course = result.recommendations[0];
  assert.equal(course.status, "pending");
  assert.equal(course.isRequired, true);
  assert.equal(course.offerings[0].semesterOrder, 1);
  assert.equal(course.offerings[0].sourceNote, "便覧の注記");
  assert.equal(course.contributions[0].code, "T01");
  assert.equal(
    course.contributions[0].reason,
    data.recommendations[0].contributions[0].reason,
  );
});

test("欠損・重複候補・不正な状態・理由・開講期を推薦へ読み替えない", () => {
  for (const change of [
    (d) => delete d.recommendations,
    (d) => (d.recommendations = null),
    (d) => d.recommendations.push(recommendation()),
    (d) => (d.recommendations[0].status = "earned"),
    (d) => (d.recommendations[0].is_required = "true"),
    (d) => (d.recommendations[0].contributions = []),
    (d) => (d.recommendations[0].contributions[0].shortage_reduction = 0),
    (d) =>
      d.recommendations[0].contributions.push({
        ...d.recommendations[0].contributions[0],
      }),
    (d) => (d.recommendations[0].offerings[0].semester_order = -1),
  ]) {
    const data = fixture();
    data.recommendations = [recommendation()];
    change(data);
    assert.throws(
      () => toGraduationResult(data),
      (error) => error.status === 502,
    );
  }
});

test("判定は本人の保存済みデータをGETし、Cookie・キャンセル・キャッシュ禁止を維持する", async (context) => {
  const calls = [];
  context.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push({ url, options });
    return Response.json(fixture());
  });
  const controller = new AbortController();
  const service = createRequirementsModule("/api");
  const result = await service.evaluate.execute(controller.signal);
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
    Response.json({ detail: "単位換算規則が未確認です" }, { status: 409 }),
  );
  await assert.rejects(
    repo.evaluate(),
    (error) =>
      error.status === 409 && error.message === "単位換算規則が未確認です",
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

test("適用年度が未確認でもAPIの判定と単位をそのまま表示へ渡す", () => {
  for (const judgment of ["pass", "fail"]) {
    const data = fixture();
    data.curriculum.verification_status = "unverified";
    data.result = judgment;
    const result = toGraduationResult(data);
    assert.equal(result.result, judgment);
    assert.equal(result.total.earnedCredits, data.total.earned_credits);
    assert.equal(result.total.shortage, data.total.shortage);
    assert.equal(data.curriculum.verification_status, "unverified");
  }
});

test("不正・欠落した成功応答を結果画面へ渡さない", () => {
  const changes = [
    (data) => (data.result = "unknown"),
    (data) => (data.total.shortage = -1),
    (data) => (data.total.earned_credits = 1.5),
    (data) => (data.data_revision = null),
    (data) => (data.curriculum.verification_status = "unknown"),
    (data) => (data.curriculum.verification_status = undefined),
    (data) => (data.evaluated_at = "invalid"),
    (data) => (data.requirements = []),
    (data) => data.requirements.push(data.requirements[0]),
    (data) => (data.requirements[0].kind = "unknown"),
    (data) => (data.requirements[0].parent_id = undefined),
    (data) => (data.missing_required_courses = null),
    (data) => (data.missing_required_courses[0].credits = 0),
    (data) => (data.allocations = null),
    (data) => (data.external_allocations = null),
    (data) => (data.warnings = null),
    (data) => (data.warnings = ["unknown"]),
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

test("他学部の算入と自由科目を分け、配分が必要な結果だけ注意書きへ渡す", () => {
  const data = fixture();
  assert.deepEqual(toGraduationResult(data).warnings, []);
  data.external_allocations = [
    {
      rule_id: "rule",
      target_classification_id: "foundation",
      target_name: "専門基礎",
      earned_credits: 8,
      credited_credits: 6,
      free_credits: 2,
    },
  ];
  data.warnings = ["provisional_external_allocation"];
  const result = toGraduationResult(data);
  assert.equal(result.externalAllocations[0].creditedCredits, 6);
  assert.equal(result.externalAllocations[0].freeCredits, 2);
  assert.deepEqual(result.warnings, ["provisional_external_allocation"]);
  data.external_allocations[0].free_credits = 3;
  assert.throws(
    () => toGraduationResult(data),
    (error) => error.status === 502,
  );
});

test("推薦導入前の履歴を再計算せず推薦情報なしとして読む", () => {
  const saved = savedCheck();
  delete saved.result.recommendations;
  assert.equal(toSavedCheck(saved).result.recommendations, null);
  saved.result.recommendations = [recommendation()];
  assert.equal(toSavedCheck(saved).result.recommendations[0].name, "候補科目");
});

test("チェックは保存済みの成績版とCSRFをPOSTし、保存した判定を返す", async (context) => {
  const calls = [];
  context.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push({ url, options });
    return Response.json(savedCheck(), { status: 201 });
  });
  const service = createRequirementsModule("/api");
  const check = await service.createCheck.execute(2, "c".repeat(64));
  assert.equal(check.id, checkId);
  assert.equal(check.input.dataRevision, 2);
  assert.equal(check.result.total.shortage, 2);
  // 科目名は保存済みの判定結果から引き、ない科目は名前なしのまま保持する。
  assert.deepEqual(
    check.input.grades.map((grade) => [grade.courseName, grade.gradeCode]),
    [
      ["必修科目", "D"],
      [null, null],
    ],
  );
  const { url, options } = calls[0];
  assert.equal(url, "/api/checks");
  assert.equal(options.method, "POST");
  assert.equal(options.body, JSON.stringify({ expected_revision: 2 }));
  assert.equal(options.headers["X-CSRF-Token"], "c".repeat(64));
  assert.equal(options.cache, "no-store");
  await assert.rejects(
    service.createCheck.execute(3, "c".repeat(64)),
    (error) => error.status === 502,
  );
});

test("履歴一覧は範囲を指定してGETし、保存時の要約を返す", async (context) => {
  const calls = [];
  const fetch = context.mock.method(
    globalThis,
    "fetch",
    async (url, options) => {
      calls.push({ url, options });
      return Response.json(checkPage());
    },
  );
  const service = createRequirementsModule("/api");
  const controller = new AbortController();
  const page = await service.listChecks.execute(
    { limit: 20, offset: 20 },
    controller.signal,
  );
  assert.equal(calls[0].url, "/api/checks?limit=20&offset=20");
  assert.equal(calls[0].options.method, "GET");
  assert.equal(calls[0].options.signal, controller.signal);
  assert.equal(page.totalCount, 21);
  assert.equal(page.checks[0].curriculum.name, "当時の課程");
  assert.equal(page.checks[0].curriculum.revision, 3);
  assert.equal(page.checks[0].total.requiredCredits, 10);
  // 要求と異なる範囲の応答は表示しない。
  await assert.rejects(
    service.listChecks.execute({ limit: 20, offset: 0 }),
    (error) => error.status === 502,
  );
  fetch.mock.mockImplementation(async () =>
    Response.json({ detail: "ログインしてください。" }, { status: 401 }),
  );
  await assert.rejects(
    service.listChecks.execute({ limit: 20, offset: 0 }),
    (error) =>
      error.status === 401 && error.message === "ログインしてください。",
  );
});

test("過去の判定は本人のIDでGETし、別IDの応答や404を表示しない", async (context) => {
  const calls = [];
  const fetch = context.mock.method(globalThis, "fetch", async (url) => {
    calls.push(url);
    return Response.json(savedCheck());
  });
  const service = createRequirementsModule("/api");
  assert.equal(
    (await service.getCheck.execute(checkId)).createdAt,
    "2026-10-16T00:00:00Z",
  );
  assert.equal(calls[0], `/api/checks/${checkId}`);
  await assert.rejects(
    service.getCheck.execute("00000000-0000-4000-8000-000000000002"),
    (error) => error.status === 502,
  );
  fetch.mock.mockImplementation(async () =>
    Response.json({ detail: "判定履歴が見つかりません。" }, { status: 404 }),
  );
  await assert.rejects(
    service.getCheck.execute(checkId),
    (error) =>
      error.status === 404 && error.message === "判定履歴が見つかりません。",
  );
});

test("不正・矛盾した履歴を画面へ渡さない", () => {
  const checkChanges = [
    (data) => (data.input.data_revision = 3),
    (data) => (data.created_at = "2026-10-17T00:00:00Z"),
    (data) => (data.created_at = "invalid"),
    (data) => (data.input.grades = null),
    (data) => (data.input.grades[0].grade_code = null),
    (data) => (data.input.grades[1].grade_code = "A"),
    (data) => (data.input.grades[0].result_status = "unknown"),
    (data) => (data.input.grades[0].attempt_no = 0),
    (data) => (data.result.courses = undefined),
    (data) => (data.result.result = "unknown"),
  ];
  for (const change of checkChanges) {
    const data = savedCheck();
    change(data);
    assert.throws(
      () => toSavedCheck(data),
      (error) => error.status === 502,
    );
  }
  const pageChanges = [
    (data) => (data.checks = null),
    (data) => (data.limit = 0),
    (data) => (data.total_count = 20),
    (data) => {
      // 件数の範囲内でも、指定件数を超える一覧は表示しない。
      data.checks = [data.checks[0], data.checks[0]];
      data.limit = 1;
      data.total_count = 30;
    },
    (data) => (data.checks[0].result = "unknown"),
    (data) => (data.checks[0].curriculum.revision = 0),
    (data) => (data.checks[0].total.shortage = -1),
    (data) => (data.checks[0].created_at = "invalid"),
  ];
  for (const change of pageChanges) {
    const data = checkPage();
    change(data);
    assert.throws(
      () => toCheckPage(data),
      (error) => error.status === 502,
    );
  }
  assert.deepEqual(
    toCheckPage({ checks: [], limit: 20, offset: 40, total_count: 3 }).checks,
    [],
  );
});

test("ダッシュボードはGETで保存済みの概要を取得し、履歴保存を呼ばない", async (context) => {
  const calls = [];
  context.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push({ url, options });
    return Response.json(dashboardFixture());
  });
  const service = createRequirementsModule("/api");
  const controller = new AbortController();
  const result = await service.dashboard.execute(controller.signal);
  assert.equal(result.dataRevision, 2);
  assert.equal(result.curriculumRevision, 1);
  assert.equal(result.gradeCount, 3);
  assert.equal(result.total.earnedCredits, 8);
  assert.equal(result.categories[0].kind, "classification_total");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "/api/me/dashboard");
  assert.equal(calls[0].options.method, "GET");
  assert.equal(calls[0].options.body, undefined);
  assert.equal(calls[0].options.cache, "no-store");
  assert.equal(calls[0].options.signal, controller.signal);
});

test("概要の0件と不正応答・設定不足・通信失敗・中断を区別する", async (context) => {
  const repo = new HttpGraduationRepository("/api");
  const fetch = context.mock.method(globalThis, "fetch", async () =>
    Response.json(dashboardFixture()),
  );
  const empty = dashboardFixture();
  empty.grade_count = 0;
  empty.total.earned_credits = empty.total.credited_credits = 0;
  fetch.mock.mockImplementation(async () => Response.json(empty));
  assert.equal((await repo.dashboard()).gradeCount, 0);
  for (const change of [
    (data) => (data.curriculum_revision = 5),
    (data) => (data.grade_count = -1),
    (data) => (data.grade_count = null),
    (data) => (data.data_revision = null),
    (data) => (data.evaluated_at = "invalid"),
    (data) => (data.result = "unknown"),
    (data) => (data.total.shortage = -1),
    (data) => (data.categories = null),
    (data) => data.categories.push(data.categories[0]),
    (data) => (data.categories[0].kind = "total"),
    (data) => (data.warnings = ["unknown"]),
  ]) {
    const data = dashboardFixture();
    change(data);
    fetch.mock.mockImplementation(async () => Response.json(data));
    await assert.rejects(repo.dashboard(), (error) => error.status === 502);
  }
  for (const status of [401, 409, 503]) {
    fetch.mock.mockImplementation(async () =>
      Response.json({ detail: "概要を取得できません" }, { status }),
    );
    await assert.rejects(
      repo.dashboard(),
      (error) =>
        error.status === status && error.message === "概要を取得できません",
    );
  }
  fetch.mock.mockImplementation(async () => {
    throw new TypeError("offline");
  });
  await assert.rejects(repo.dashboard(), (error) => error.status === 0);
  const abort = new DOMException("Aborted", "AbortError");
  fetch.mock.mockImplementation(async () => {
    throw abort;
  });
  await assert.rejects(repo.dashboard(), (error) => error === abort);
});

test("修了判定の保留・本人申告・根拠を保持し、単位だけの保留応答は拒否する", () => {
  const data = fixture();
  data.result = "pending";
  data.degree_level = "master";
  data.completion_conditions = [
    {
      code: "thesis",
      name: "修士論文の審査",
      status: "unknown",
      source_document: "https://example.test/rules.pdf",
      source_pages: "PDF1",
    },
  ];
  const result = toGraduationResult(data);
  assert.equal(result.result, "pending");
  assert.equal(result.degreeLevel, "master");
  assert.equal(result.completionConditions[0].status, "unknown");
  assert.equal(result.completionConditions[0].sourcePages, "PDF1");
  assert.throws(() =>
    toGraduationResult({
      ...data,
      total: { ...data.total, result: "pending" },
    }),
  );
  assert.throws(() =>
    toGraduationResult({
      ...data,
      completion_conditions: [
        { ...data.completion_conditions[0], status: true },
      ],
    }),
  );
});

test("修了条件の本人回答を成績版とともに送信し、履歴の結果を保持する", async (context) => {
  const payload = savedCheck();
  context.mock.method(globalThis, "fetch", async (_url, options) => {
    assert.deepEqual(JSON.parse(options.body), {
      expected_revision: 2,
      completion_answers: [{ code: "thesis", status: "met" }],
    });
    return Response.json(payload, { status: 201 });
  });
  const repository = new HttpGraduationRepository("/api");
  await repository.createCheck(2, "csrf", undefined, [
    { code: "thesis", status: "met" },
  ]);
});
