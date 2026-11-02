import assert from "node:assert/strict";

import test from "node:test";

import { pathToFileURL } from "node:url";

import { join } from "node:path";

const load = (path) =>
  import(pathToFileURL(join(process.env.SUBJECT_TEST_BUILD_DIRECTORY, path)));

const { filterRequirements } = await load(
  "modules/requirements/application/services/filterRequirements.js",
);

test("区分で絞ると子孫条件を含み、他区分と総単位を含まない", () => {
  const rows = [
    { id: "total", kind: "total", parentId: null },
    { id: "general", kind: "classification_total", parentId: "total" },
    { id: "group", kind: "selective_group", parentId: "general" },
    { id: "humanities", kind: "subminimum", parentId: "group" },
    { id: "specialty", kind: "classification_total", parentId: "total" },
    { id: "required", kind: "required_courses", parentId: "specialty" },
  ];
  assert.deepEqual(
    filterRequirements(rows, "general").map((row) => row.id),
    ["general", "group", "humanities"],
  );
  assert.deepEqual(
    filterRequirements(rows, "specialty").map((row) => row.id),
    ["specialty", "required"],
  );
  assert.deepEqual(filterRequirements(rows, null), rows);
  assert.deepEqual(filterRequirements(rows, "old-curriculum"), rows);
});

test("条件の親参照が欠けたり循環しても絞り込みが停止する", () => {
  const rows = [
    { id: "general", kind: "classification_total", parentId: null },
    { id: "orphan", kind: "subminimum", parentId: "missing" },
    { id: "a", kind: "subminimum", parentId: "b" },
    { id: "b", kind: "subminimum", parentId: "a" },
  ];
  assert.deepEqual(filterRequirements(rows, "general"), [rows[0]]);
});

const { buildRequirementMatrix } = await load(
  "modules/requirements/application/services/buildRequirementMatrix.js",
);

function requirement(id, kind, parentId, classificationId, name = id) {
  return {
    id,
    code: id,
    name,
    kind,
    parentId,
    classificationId,
    requiredCredits: 2,
    earnedCredits: 1,
    creditedCredits: 1,
    shortage: 1,
    result: "fail",
  };
}

function matrixFixture() {
  return [
    requirement("total", "total", null, null, "総必要単位"),
    requirement(
      "general",
      "classification_total",
      "total",
      "general",
      "実学基礎科目合計",
    ),
    requirement(
      "required",
      "required_courses",
      "general",
      "general",
      "実学基礎科目の必修",
    ),
    requirement(
      "elective",
      "elective_total",
      "general",
      "general",
      "実学基礎科目の選択",
    ),
    // 親と同じ分類IDでも、選択必修は独立した科目群として保持する。
    requirement(
      "combined",
      "selective_group",
      "general",
      "general",
      "総合・人文・社会・自然科学・ウェルビーイングの選択必修",
    ),
    requirement(
      "humanities",
      "subminimum",
      "combined",
      "humanities",
      "人文の内訳最低単位",
    ),
    requirement(
      "language",
      "selective_group",
      "general",
      "language",
      "外国語の選択必修",
    ),
    requirement(
      "specialty",
      "classification_total",
      "total",
      "specialty",
      "専門教育科目合計",
    ),
  ];
}

test("科目区分を階層にし、必修・選択を親区分の列へまとめ、総単位は表から分離する", () => {
  const input = matrixFixture();
  const snapshot = structuredClone(input);
  const rows = buildRequirementMatrix(input);
  assert.deepEqual(
    rows.map((row) => [row.id, row.depth]),
    [
      ["general", 0],
      ["combined", 1],
      ["humanities", 2],
      ["language", 1],
      ["specialty", 0],
    ],
  );
  assert.equal(rows[0].cells.classification_total[0], input[1]);
  assert.equal(rows[0].cells.required_courses[0], input[2]);
  assert.equal(rows[0].cells.elective_total[0], input[3]);
  assert.equal(rows[1].cells.selective_group[0], input[4]);
  assert.equal(rows[2].cells.selective_group[0], input[5]);
  assert.deepEqual(input, snapshot);
  assert.deepEqual(
    rows
      .flatMap((row) => Object.values(row.cells).flat())
      .map((r) => r.id)
      .sort(),
    input
      .filter((r) => r.kind !== "total")
      .map((r) => r.id)
      .sort(),
  );
  assert.deepEqual(
    buildRequirementMatrix(filterRequirements(input, "specialty")).map(
      (r) => r.id,
    ),
    ["specialty"],
  );
});

test("分類の異なる条件・親の欠損・循環・同じ列の複数条件を消さず推測で統合しない", () => {
  const input = [
    requirement("root", "classification_total", null, "root"),
    requirement("a", "required_courses", "root", "root"),
    requirement("b", "required_courses", "root", "root"),
    requirement("other", "required_courses", "root", "other"),
    requirement("unknown", "elective_total", "root", null),
    requirement("orphan", "selective_group", "missing", "orphan"),
    requirement("cycle-a", "subminimum", "cycle-b", "a"),
    requirement("cycle-b", "subminimum", "cycle-a", "b"),
  ];
  const rows = buildRequirementMatrix(input);
  assert.deepEqual(
    rows[0].cells.required_courses.map((r) => r.id),
    ["a", "b"],
  );
  assert.ok(rows.some((r) => r.id === "other" && r.depth === 1));
  assert.ok(rows.some((r) => r.id === "unknown" && r.depth === 1));
  const conditions = rows.flatMap((r) => Object.values(r.cells).flat());
  assert.equal(conditions.length, input.length);
  assert.equal(new Set(conditions.map((r) => r.id)).size, input.length);
  assert.deepEqual(buildRequirementMatrix([]), []);
});

test("判定結果は科目区分だけを行見出しにし、全条件の算入・必要単位と判定を日英で表示する", async () => {
  const { createElement } = await import("react");
  const { renderToStaticMarkup } = await import("react-dom/server");
  const { I18nextProvider } = await import("react-i18next");
  const { createSiteI18n } = await load("i18n/createI18n.js");
  const { RequirementMatrix } = await load(
    "apps/web/components/requirements/RequirementMatrix.js",
  );
  const input = matrixFixture();
  const i18n = createSiteI18n({ languages: ["ja"] });
  const render = () =>
    renderToStaticMarkup(
      createElement(
        I18nextProvider,
        { i18n },
        createElement(RequirementMatrix, { requirements: input }),
      ),
    );
  const html = render();
  const headings = [...html.matchAll(/<th scope="row"[^>]*>(.*?)<\/th>/g)].map(
    (match) => match[1].replace(/<[^>]*>/g, ""),
  );
  assert.deepEqual(headings, [
    "実学基礎科目",
    "総合・人文・社会・自然科学・ウェルビーイング",
    "人文（最低2単位）",
    "外国語",
    "専門教育科目",
  ]);
  assert.doesNotMatch(html, /総必要単位|<th scope="col">内訳最低<\/th>/);
  assert.doesNotMatch(html, /colSpan=/i);
  const humanitiesRow = html.match(
    /<tr[^>]*><th[^>]*>人文（最低2単位）<\/th>(.*?)<\/tr>/,
  )[1];
  const cells = [...humanitiesRow.matchAll(/<td[^>]*>(.*?)<\/td>/g)].map(
    (match) => match[1].replace(/<[^>]*>/g, ""),
  );
  assert.deepEqual(cells, ["—", "—", "—", "1 / 2未達成"]);
  for (const row of input.slice(1))
    assert.ok(html.includes(`aria-label="${row.name}"`), row.name);
  assert.match(html, /1 \/ 2/);
  assert.doesNotMatch(html, /修得1・不足1|requirement-credit-detail/);
  assert.match(html, /未達成/);
  assert.match(html, /padding-inline-start:52px/);
  await i18n.changeLanguage("en");
  const english = render();
  assert.match(english, /Required elective/);
  assert.match(english, /1 \/ 2/);
  assert.doesNotMatch(
    english,
    /Earned 1 · remaining 1|requirement-credit-detail/,
  );
  assert.match(english, /実学基礎科目/);
  assert.match(english, /人文 \(minimum 2 credits\)/);
});

test("同じ科目区分の必修内訳と選択必修を同じ行へ置き、必修だけの区分も表示する", () => {
  const input = matrixFixture();
  const languageRequired = {
    ...requirement(
      "language-required",
      "required_courses",
      "general",
      "language",
      "外国語の必修",
    ),
    requiredCredits: 4,
    creditedCredits: 2,
  };
  const careerRequired = {
    ...requirement(
      "career-required",
      "required_courses",
      "general",
      "career",
      "キャリア教育の必修",
    ),
    requiredCredits: 6,
    creditedCredits: 0,
  };
  const rows = buildRequirementMatrix([
    ...input,
    languageRequired,
    careerRequired,
  ]);
  const language = rows.find((row) => row.id === "language");
  assert.equal(language.depth, 1);
  assert.equal(language.cells.required_courses[0], languageRequired);
  assert.equal(
    language.cells.selective_group[0],
    input.find((row) => row.id === "language"),
  );
  assert.equal(
    rows.find((row) => row.id === "general").cells.required_courses[0].id,
    "required",
  );
  assert.equal(rows.find((row) => row.id === "career-required").depth, 1);
  assert.equal(
    rows.find((row) => row.id === "career-required").cells.required_courses[0],
    careerRequired,
  );
  assert.equal(
    rows.flatMap((row) => Object.values(row.cells).flat()).length,
    input.length + 1,
  );
});
