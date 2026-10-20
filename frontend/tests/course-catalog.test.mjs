import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;
const load = (path) => import(pathToFileURL(join(directory, path)));
const { HttpCourseCatalogRepository } = await load(
  "modules/subjects/infrastructure/course-catalog/HttpCourseCatalogRepository.js",
);
const { GetCourseCatalogUseCase } = await load(
  "modules/subjects/application/use_cases/GetCourseCatalogUseCase.js",
);
const catalog = await load(
  "modules/subjects/application/services/filterCatalogCourses.js",
);

const curriculum = {
  curriculum_id: "cur",
  name: "2026年度便覧",
  verification_status: "unverified",
  admission_year_from: null,
  admission_year_to: null,
  source_document: "学生便覧",
  source_pages: "83-94",
};
const course = (id, overrides = {}) => ({
  course_id: id,
  code: `CS-${id}`,
  name: `科目${id}`,
  credits: 2,
  offering_faculty_name: "CS学部",
  offering_department_name: null,
  offering_specialization_name: null,
  teaching_type: "lecture",
  teaching_type_label: "講義",
  offerings: [
    {
      term_code: "first",
      semester_order: 1,
      academic_year: null,
      source_note: null,
    },
  ],
  placement: {
    classification_path: [
      { id: "root", name: "専門基礎" },
      { id: "child", name: "数学" },
    ],
    course_type: "required",
  },
  ...overrides,
});
const category = (id, parent = null) => ({
  id,
  code: id,
  name: id,
  parent_id: parent,
  level: parent ? 1 : 0,
  display_order: 0,
});

function serve(
  context,
  courses,
  categories = [category("root"), category("child", "root")],
) {
  const requests = [];
  context.mock.method(globalThis, "fetch", async (url, options) => {
    requests.push({ url, options });
    return Response.json(
      url.endsWith("/courses")
        ? { curriculum, courses }
        : { curriculum, categories },
    );
  });
  return requests;
}

test("科目一覧と分類を同じ課程として取得し、課程外の科目に分類を推測しない", async (context) => {
  const requests = serve(context, [
    course("a"),
    course("b", {
      placement: null,
      offering_faculty_name: "工学部",
      offering_department_name: "機械工学科",
    }),
  ]);
  const controller = new AbortController();
  const useCase = new GetCourseCatalogUseCase(
    new HttpCourseCatalogRepository("/api"),
  );
  const result = await useCase.execute(controller.signal);
  assert.deepEqual(requests.map((r) => r.url).sort(), [
    "/api/categories",
    "/api/courses",
  ]);
  for (const { options } of requests) {
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    assert.equal(options.signal, controller.signal);
  }
  assert.equal(result.curriculum.verificationStatus, "unverified");
  assert.equal(result.courses[0].placement.courseType, "required");
  assert.equal(result.courses[1].placement, null);
  assert.equal(result.categories[1].parentId, "root");

  const all = result.courses;
  const filters = { ...catalog.emptyCatalogFilters };
  assert.deepEqual(
    catalog.filterCatalogCourses(all, { ...filters, categoryId: "root" }),
    [all[0]],
  );
  assert.deepEqual(
    catalog.filterCatalogCourses(all, { ...filters, faculty: "工学部" }),
    [all[1]],
  );
  assert.deepEqual(
    catalog.filterCatalogCourses(all, { ...filters, department: "機械工学科" }),
    [all[1]],
  );
  assert.deepEqual(
    catalog.filterCatalogCourses(all, { ...filters, semester: "second" }),
    [],
  );
  assert.deepEqual(
    catalog.filterCatalogCourses(all, { ...filters, search: "ｃｓ-Ａ" }),
    [all[0]],
  );
  assert.deepEqual(
    catalog.filterCatalogCourses(all, {
      ...filters,
      categoryId: "root",
      faculty: "工学部",
    }),
    [],
  );
  assert.deepEqual(
    catalog.facultyOptions(all),
    ["CS学部", "工学部"].sort((a, b) => a.localeCompare(b, "ja")),
  );
  assert.deepEqual(catalog.departmentOptions(all, "CS学部"), []);
  assert.deepEqual(catalog.departmentOptions(all, ""), ["機械工学科"]);
});

test("所属未設定・未認証・不正応答を区別する", async (context) => {
  const repository = new HttpCourseCatalogRepository("/api");
  const fetch = context.mock.method(globalThis, "fetch", async () =>
    Response.json({ detail: "所属課程を設定してください" }, { status: 409 }),
  );
  const signal = new AbortController().signal;
  await assert.rejects(
    repository.getCatalog(signal),
    (error) =>
      error.status === 409 && error.message === "所属課程を設定してください",
  );
  fetch.mock.mockImplementation(async () =>
    Response.json({ detail: "ログインしてください" }, { status: 401 }),
  );
  await assert.rejects(
    repository.getCatalog(signal),
    (error) => error.status === 401,
  );
  for (const invalid of [
    {
      curriculum,
      courses: [
        course("a", {
          placement: { classification_path: [], course_type: "free" },
        }),
      ],
    },
    { curriculum, courses: [course("a", { credits: 0 })] },
    { curriculum: { ...curriculum, curriculum_id: "other" }, courses: [] },
  ]) {
    fetch.mock.mockImplementation(async (url) =>
      Response.json(
        url.endsWith("/courses") ? invalid : { curriculum, categories: [] },
      ),
    );
    await assert.rejects(
      repository.getCatalog(signal),
      (error) => error.status === 502,
    );
  }
});
