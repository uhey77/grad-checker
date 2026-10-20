import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;
const { HttpProfileRepository } = await import(
  pathToFileURL(
    join(
      directory,
      "modules/profiles/infrastructure/external_services/HttpProfileRepository.js",
    ),
  )
);
const { createProfilesModule } = await import(
  pathToFileURL(join(directory, "modules/profiles/composition.js"))
);
const { toPrograms, toProfile } = await import(
  pathToFileURL(
    join(
      directory,
      "modules/profiles/infrastructure/external_services/schemas/mappers.js",
    ),
  )
);

const option = {
  program_id: "program",
  curriculum_id: "curriculum",
  faculty_name: "CS学部",
  department_name: null,
  specialization_name: "先進情報専攻",
  course_name: "人工知能",
  curriculum_name: "2026年度便覧",
  revision: 1,
  verification_status: "unverified",
  admission_year_from: null,
  admission_year_to: null,
  source_document: "学生便覧",
  source_pages: "83-94",
};
const initial = {
  student_id: "own",
  login_name: "owner",
  program_id: null,
  curriculum_id: null,
  data_revision: 0,
};

test("所属APIのDTO変換・本人Cookie・CSRF・更新版の契約", async (context) => {
  const requests = [];
  const controller = new AbortController();
  context.mock.method(globalThis, "fetch", async (url, options) => {
    requests.push({ url, options });
    return Response.json(
      url.endsWith("/programs")
        ? { programs: [option] }
        : url.endsWith("/me/program")
          ? {
              ...initial,
              program_id: "program",
              curriculum_id: "curriculum",
              data_revision: 1,
            }
          : initial,
    );
  });
  const useCases = createProfilesModule("/api");
  const options = await useCases.listPrograms.execute(controller.signal);
  assert.equal(options[0].verificationStatus, "unverified");
  assert.equal(options[0].admissionYearFrom, null);
  assert.equal(options[0].courseName, "人工知能");
  const profile = await useCases.getProfile.execute(controller.signal);
  assert.equal(profile.curriculumId, null);
  const saved = await useCases.saveProgram.execute(
    {
      programId: "program",
      curriculumId: "curriculum",
      expectedRevision: profile.dataRevision,
    },
    "csrf",
    controller.signal,
  );
  assert.equal(saved.dataRevision, 1);
  assert.equal(requests.at(-1).options.method, "PUT");
  assert.equal(requests.at(-1).options.headers["X-CSRF-Token"], "csrf");
  assert.deepEqual(JSON.parse(requests.at(-1).options.body), {
    program_id: "program",
    curriculum_id: "curriculum",
    expected_revision: 0,
  });
  for (const { url, options } of requests) {
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    assert.equal(options.signal, controller.signal);
    assert.ok(!url.includes("student_id"));
  }
});

test("未認証・更新競合・通信失敗を区別しキャンセルを保持する", async (context) => {
  const repository = new HttpProfileRepository("/api");
  const fetch = context.mock.method(globalThis, "fetch", async () =>
    Response.json({ detail: "再取得してください" }, { status: 409 }),
  );
  await assert.rejects(
    repository.saveProgram(
      { programId: "p", curriculumId: "c", expectedRevision: 0 },
      "csrf",
    ),
    (error) => error.status === 409 && error.message === "再取得してください",
  );
  fetch.mock.mockImplementation(async () =>
    Response.json({ detail: "ログインしてください" }, { status: 401 }),
  );
  await assert.rejects(
    repository.getProfile(),
    (error) => error.status === 401,
  );
  fetch.mock.mockImplementation(async () => {
    throw new TypeError("network");
  });
  await assert.rejects(repository.getProfile(), (error) => error.status === 0);
  const controller = new AbortController();
  controller.abort();
  const reason = new DOMException("Aborted", "AbortError");
  fetch.mock.mockImplementation(async () => {
    throw reason;
  });
  await assert.rejects(
    repository.getProfile(controller.signal),
    (error) => error === reason,
  );
});

test("欠損・不正な所属と未確認状態の誤変換を拒否する", () => {
  for (const invalid of [
    null,
    {},
    { ...initial, data_revision: -1 },
    { ...initial, data_revision: 0.5 },
    { ...initial, program_id: "p" },
  ]) {
    assert.throws(
      () => toProfile(invalid),
      (error) => error.status === 502,
    );
  }
  for (const programs of [
    [{}],
    [option, option],
    [{ ...option, verification_status: "unknown" }],
    [{ ...option, verification_status: "verified" }],
    [{ ...option, admission_year_from: 2027, admission_year_to: 2026 }],
  ]) {
    assert.throws(
      () => toPrograms({ programs }),
      (error) => error.status === 502,
    );
  }
  assert.deepEqual(toPrograms({ programs: [] }), []);
});

test("課程別の対応状況と未確認理由・大学院条件を所属選択へ渡す", () => {
  const data = {
    ...option,
    completion_policy: {
      degree_level: "master",
      campus: "hachioji",
      catalog_status: "verified",
      requirements_status: "unverified",
      rules_status: "unverified",
      unresolved_reasons: ["学位申請要件が未確認"],
      source_document: "https://example.test/source.pdf",
      source_pages: "PDF1",
      non_credit_conditions: [
        {
          code: "thesis",
          name: "論文の審査合格",
          source_document: "https://example.test/source.pdf",
          source_pages: "PDF1",
        },
      ],
    },
  };
  const policy = toPrograms({ programs: [data] })[0].completionPolicy;
  assert.equal(policy.degreeLevel, "master");
  assert.deepEqual(policy.unresolvedReasons, ["学位申請要件が未確認"]);
  assert.equal(policy.conditions[0].code, "thesis");
  assert.throws(() =>
    toPrograms({
      programs: [
        {
          ...data,
          completion_policy: {
            ...data.completion_policy,
            degree_level: "other",
          },
        },
      ],
    }),
  );
});
