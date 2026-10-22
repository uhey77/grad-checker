import assert from "node:assert/strict";

import test from "node:test";

import { pathToFileURL } from "node:url";

import { join } from "node:path";

async function loadModule(path) {
  return import(
    pathToFileURL(join(process.env.SUBJECT_TEST_BUILD_DIRECTORY, path)).href
  );
}

const { filterSubjects, emptyFilters } = await loadModule(
  "modules/subjects/application/services/filterSubjects.js",
);

const { toSubjectList } = await loadModule(
  "modules/subjects/infrastructure/external_services/schemas/subject-list/mappers.js",
);

const { ListSubjectProgramsUseCase, GetSubjectListUseCase } = await loadModule(
  "modules/subjects/public.js",
);

const subjectUseCases = (repository) => ({
  listPrograms: new ListSubjectProgramsUseCase(repository),
  getSubjectList: new GetSubjectListUseCase(repository),
});

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

const { sortSubjects } = await loadModule(
  "modules/subjects/application/services/sortSubjects.js",
);

const { offeringLabels, programLabel, sharedAcrossYears, joinLabels } =
  await loadModule("apps/web/components/subjects/labels.js");

test("検索は全角・大文字・ローマ数字を正規化し、複数条件をANDで適用する", () => {
  const courses = toSubjectList(dto).subjects;
  const filters = {
    search: "  ｗｅｂプログラミングI  ",
    category: "professional",
    type: "selective",
    semester: "second",
    faculty: "CS",
  };
  assert.deepEqual(
    filterSubjects(courses, filters).map((x) => x.id),
    ["web"],
  );
  for (const [key, value] of Object.entries({
    search: "不存在",
    category: "other",
    type: "elective",
    semester: "other",
    faculty: "other",
  })) {
    assert.deepEqual(filterSubjects(courses, { ...filters, [key]: value }), []);
  }
  assert.deepEqual(filterSubjects(courses, emptyFilters), courses);
  assert.deepEqual(filterSubjects([], emptyFilters), []);
});

test("ユースケースは注入した取得先に課程IDとキャンセル信号を渡し、失敗を伝える", async () => {
  const signal = new AbortController().signal;
  const subjectList = toSubjectList(dto);
  const calls = [];
  const useCases = subjectUseCases({
    async listPrograms(received) {
      calls.push(received);
      return [subjectList.program];
    },
    async getSubjectList(id, received) {
      calls.push([id, received]);
      return subjectList;
    },
  });
  assert.deepEqual(await useCases.listPrograms.execute(signal), [
    subjectList.program,
  ]);
  assert.equal(
    await useCases.getSubjectList.execute("social", signal),
    subjectList,
  );
  assert.deepEqual(calls, [signal, ["social", signal]]);
  const failed = subjectUseCases({
    listPrograms: async () => {
      throw new Error("取得失敗");
    },
  });
  await assert.rejects(failed.listPrograms.execute(signal), /取得失敗/);
});

test("課程・分類・開講元は全画面で同じ表記にする", () => {
  // 所属設定の選択肢（学科あり）と科目一覧の課程（学科なし）を同じ関数で表す。
  assert.equal(
    programLabel({
      facultyName: "CS学部",
      departmentName: null,
      specializationName: "先進情報専攻",
      courseName: "人工知能コース",
    }),
    "CS学部 ／ 先進情報専攻 ／ 人工知能コース",
  );
  assert.equal(
    programLabel({
      facultyName: "CS学部",
      specializationName: "社会情報専攻",
      courseName: null,
    }),
    "CS学部 ／ 社会情報専攻",
  );
  assert.equal(
    joinLabels([null, "社会情報専攻", "講義・演習"]),
    "社会情報専攻 / 講義・演習",
  );
  const offering = (sourceNote) => ({
    semesterOrder: 3,
    termCode: "first",
    academicYear: null,
    sourceNote,
  });
  assert.ok(sharedAcrossYears([offering(null), offering("学年共通開講")]));
  assert.ok(!sharedAcrossYears([offering(null)]));
});

test("並べ替えは単位・最初の開講期を比較し、同順位の便覧順と元データを保つ", () => {
  const base = toSubjectList(dto).subjects[0];
  const courses = [
    {
      ...base,
      id: "b",
      name: "B",
      credits: 3,
      offerings: [{ ...base.offerings[0], semesterOrder: 5 }],
    },
    {
      ...base,
      id: "a",
      name: "A",
      credits: 1,
      offerings: [{ ...base.offerings[0], semesterOrder: 2 }],
    },
    { ...base, id: "c", name: "C", credits: 3, offerings: [] },
  ];
  const ids = (order) => sortSubjects(courses, order).map((x) => x.id);
  assert.deepEqual(ids("handbook"), ["b", "a", "c"]);
  assert.deepEqual(ids("name"), ["a", "b", "c"]);
  assert.deepEqual(ids("credits-ascending"), ["a", "b", "c"]);
  assert.deepEqual(ids("credits-descending"), ["b", "c", "a"]);
  assert.deepEqual(ids("semester"), ["a", "b", "c"]);
  assert.deepEqual(
    courses.map((x) => x.id),
    ["b", "a", "c"],
  );
  assert.notEqual(sortSubjects(courses, "handbook"), courses);
});

test("同学年の両学期だけをまとめ、異なる学年の前期と後期を混同しない", () => {
  const offering = (semesterOrder, termCode) => ({
    semesterOrder,
    termCode,
    academicYear: null,
    sourceNote: null,
  });
  assert.deepEqual(
    offeringLabels([
      offering(4, "second"),
      offering(3, "first"),
      offering(3, "first"),
    ]),
    ["2年次前期・後期"],
  );
  assert.deepEqual(
    offeringLabels([offering(1, "first"), offering(4, "second")]),
    ["1年次前期", "2年次後期"],
  );
  assert.deepEqual(offeringLabels([]), []);
});
