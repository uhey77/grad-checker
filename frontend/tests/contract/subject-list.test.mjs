import assert from "node:assert/strict";

import test from "node:test";

import { pathToFileURL } from "node:url";

import { join } from "node:path";

async function loadModule(path) {
  return import(
    pathToFileURL(join(process.env.SUBJECT_TEST_BUILD_DIRECTORY, path)).href
  );
}

const { toSubjectList } = await loadModule(
  "modules/subjects/infrastructure/external_services/schemas/subject-list/mappers.js",
);

const program = {
  curriculum_id: "social",
  name: "社会情報専攻",
  faculty_name: "CS",
  specialization_name: "社会情報専攻",
  course_name: null,
  verification_status: "unverified",
  admission_year_from: null,
  admission_year_to: null,
  source_document: "学生便覧",
  source_pages: "91–92",
};

const subject = {
  id: "web",
  code: "WEB",
  name: "WebプログラミングⅠ",
  credits: 2,
  faculty_name: "CS",
  department_name: null,
  specialization_name: null,
  teaching_type_label: "演習",
  course_type: "selective",
  classification_path: [{ id: "professional", name: "専門教育科目" }],
  offerings: [
    {
      term_code: "first",
      semester_order: 3,
      academic_year: null,
      source_note: "学年共通開講",
    },
    {
      term_code: "second",
      semester_order: 6,
      academic_year: null,
      source_note: null,
    },
  ],
};

const dto = {
  program,
  courses: [
    subject,
    { ...subject, id: "ai", name: "人工知能", course_type: "required" },
  ],
};

const { HttpSubjectListRepository } = await loadModule(
  "modules/subjects/infrastructure/external_services/subject-list/HttpSubjectListRepository.js",
);

const { SubjectListError } = await loadModule(
  "modules/subjects/application/errors/SubjectListError.js",
);

const { subjectListErrorMessage } = await loadModule(
  "apps/web/hooks/subjects/errors.js",
);

test("APIから分類・全開講時期・注記・適用年度の未確認を保って変換する", () => {
  const subjectList = toSubjectList(dto);
  assert.equal(subjectList.program.curriculumId, "social");
  assert.equal(subjectList.program.admissionYearFrom, null);
  assert.equal(subjectList.program.verificationStatus, "unverified");
  assert.deepEqual(
    subjectList.subjects[0].classificationPath,
    subject.classification_path,
  );
  assert.equal(subjectList.subjects[0].offerings.length, 2);
  assert.equal(subjectList.subjects[0].offerings[0].sourceNote, "学年共通開講");
  assert.equal(subjectList.subjects[0].subjectType, "selective");
  assert.equal(
    toSubjectList({
      ...dto,
      courses: [{ ...subject, course_type: "required" }],
    }).subjects[0].subjectType,
    "required",
  );
});

test("HTTP取得先はDTOを変換し、業務エラーと通信キャンセルを区別する", async () => {
  const originalFetch = globalThis.fetch;
  const repository = new HttpSubjectListRepository("/api/dev/subject-list");
  const controller = new AbortController();
  try {
    globalThis.fetch = async (url, options) => {
      assert.equal(url, "/api/dev/subject-list/social%2Ftest");
      assert.equal(options.signal, controller.signal);
      return Response.json(dto);
    };
    assert.deepEqual(
      await repository.getSubjectList("social/test", controller.signal),
      toSubjectList(dto),
    );
    for (const [status, code] of [
      [404, "not-found"],
      [409, "conflict"],
      [503, "unavailable"],
      [422, "unexpected"],
    ]) {
      globalThis.fetch = async () =>
        Response.json({ detail: "日本語のエラー" }, { status });
      await assert.rejects(
        repository.listPrograms(controller.signal),
        (error) => {
          assert.ok(error instanceof SubjectListError);
          assert.equal(error.code, code);
          assert.equal(subjectListErrorMessage(error), "日本語のエラー");
          return true;
        },
      );
    }
    globalThis.fetch = async () => {
      throw new TypeError("network");
    };
    await assert.rejects(
      repository.listPrograms(controller.signal),
      (error) => error.code === "unavailable",
    );
    globalThis.fetch = async () => new Response("not json");
    await assert.rejects(
      repository.listPrograms(controller.signal),
      (error) => error.code === "invalid-response",
    );
    const aborted = new DOMException("cancelled", "AbortError");
    globalThis.fetch = async () => {
      throw aborted;
    };
    await assert.rejects(
      repository.listPrograms(controller.signal),
      (error) => error === aborted,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
