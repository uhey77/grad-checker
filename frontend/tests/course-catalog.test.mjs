import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

async function loadModule(path) {
  return import(
    pathToFileURL(join(process.env.CATALOG_TEST_BUILD_DIRECTORY, path)).href
  );
}
const { filterCourses, emptyFilters } = await loadModule(
  "application/course-catalog/filterCourses.js",
);
const { toCatalog } = await loadModule(
  "infrastructure/course-catalog/mappers.js",
);
const { createCatalogUseCases } = await loadModule(
  "application/course-catalog/CatalogUseCases.js",
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
const course = {
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
    course,
    { ...course, id: "ai", name: "人工知能", course_type: "required" },
  ],
};

test("APIから分類・全開講時期・注記・適用年度の未確認を保って変換する", () => {
  const catalog = toCatalog(dto);
  assert.equal(catalog.program.curriculumId, "social");
  assert.equal(catalog.program.admissionYearFrom, null);
  assert.equal(catalog.program.verificationStatus, "unverified");
  assert.deepEqual(
    catalog.courses[0].classificationPath,
    course.classification_path,
  );
  assert.equal(catalog.courses[0].offerings.length, 2);
  assert.equal(catalog.courses[0].offerings[0].sourceNote, "学年共通開講");
  assert.equal(catalog.courses[0].courseType, "selective");
  assert.equal(
    toCatalog({ ...dto, courses: [{ ...course, course_type: "required" }] })
      .courses[0].courseType,
    "required",
  );
});

test("検索は全角・大文字・ローマ数字を正規化し、複数条件をANDで適用する", () => {
  const courses = toCatalog(dto).courses;
  const filters = {
    search: "  ｗｅｂプログラミングI  ",
    category: "professional",
    type: "selective",
    semester: "second",
    faculty: "CS",
  };
  assert.deepEqual(
    filterCourses(courses, filters).map((x) => x.id),
    ["web"],
  );
  for (const [key, value] of Object.entries({
    search: "不存在",
    category: "other",
    type: "elective",
    semester: "other",
    faculty: "other",
  })) {
    assert.deepEqual(filterCourses(courses, { ...filters, [key]: value }), []);
  }
  assert.deepEqual(filterCourses(courses, emptyFilters), courses);
  assert.deepEqual(filterCourses([], emptyFilters), []);
});

test("ユースケースは注入した取得先に課程IDとキャンセル信号を渡し、失敗を伝える", async () => {
  const signal = new AbortController().signal;
  const catalog = toCatalog(dto);
  const calls = [];
  const useCases = createCatalogUseCases({
    async listPrograms(received) {
      calls.push(received);
      return [catalog.program];
    },
    async getCatalog(id, received) {
      calls.push([id, received]);
      return catalog;
    },
  });
  assert.deepEqual(await useCases.listPrograms(signal), [catalog.program]);
  assert.equal(await useCases.getCatalog("social", signal), catalog);
  assert.deepEqual(calls, [signal, ["social", signal]]);
  const failed = createCatalogUseCases({
    listPrograms: async () => {
      throw new Error("取得失敗");
    },
  });
  await assert.rejects(failed.listPrograms(signal), /取得失敗/);
});

test("内側の層はReactや通信実装に依存せず、画面は通信実装を直接参照しない", async () => {
  async function scan(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = new URL(
        entry.name + (entry.isDirectory() ? "/" : ""),
        directory,
      );
      if (entry.isDirectory()) await scan(path);
      else if (/\.tsx?$/.test(entry.name)) {
        const source = await readFile(path, "utf8");
        const imports = [
          ...source.matchAll(/(?:from\s+|import\s*)["']([^"']+)["']/g),
        ].map((x) => x[1]);
        for (const dependency of imports) {
          if (directory.href.includes("/domain/"))
            assert.ok(
              !/application|infrastructure|presentation|react/.test(dependency),
              path.pathname,
            );
          if (directory.href.includes("/application/"))
            assert.ok(
              !/infrastructure|presentation|react/.test(dependency),
              path.pathname,
            );
          if (directory.href.includes("/presentation/"))
            assert.ok(!/infrastructure/.test(dependency), path.pathname);
        }
        if (!directory.href.includes("/infrastructure/"))
          assert.ok(!/\bfetch\s*\(/.test(source), path.pathname);
      }
    }
  }
  for (const layer of ["domain", "application", "presentation"])
    await scan(new URL(`../src/${layer}/`, import.meta.url));
});

const { sortCourses } = await loadModule(
  "application/course-catalog/sortCourses.js",
);
const { offeringLabels } = await loadModule(
  "presentation/course-catalog/labels.js",
);

test("並べ替えは単位・最初の開講期を比較し、同順位の便覧順と元データを保つ", () => {
  const base = toCatalog(dto).courses[0];
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
  const ids = (order) => sortCourses(courses, order).map((x) => x.id);
  assert.deepEqual(ids("handbook"), ["b", "a", "c"]);
  assert.deepEqual(ids("name"), ["a", "b", "c"]);
  assert.deepEqual(ids("credits-ascending"), ["a", "b", "c"]);
  assert.deepEqual(ids("credits-descending"), ["b", "c", "a"]);
  assert.deepEqual(ids("semester"), ["a", "b", "c"]);
  assert.deepEqual(
    courses.map((x) => x.id),
    ["b", "a", "c"],
  );
  assert.notEqual(sortCourses(courses, "handbook"), courses);
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
