import assert from "node:assert/strict";
import test from "node:test";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { I18nextProvider } from "react-i18next";

const built = (file) =>
  import(pathToFileURL(join(process.env.SUBJECT_TEST_BUILD_DIRECTORY, file)));
const { createSiteI18n } = await built("i18n/createI18n.js");
const { ShortageCourses } = await built(
  "apps/web/components/requirements/ShortageCourses.js",
);

test("不足条件に対応する候補と、推薦に含まれない未修得必修を表示する", () => {
  const condition = (id, kind, shortage) => ({ id, kind, shortage, name: id });
  const result = {
    requirements: [
      {
        ...condition("社会人基礎の必修", "required_courses", 4),
        classificationId: "social",
      },
      {
        ...condition("数理の必修", "required_courses", 2),
        classificationId: "math",
      },
      condition("選択条件", "elective_total", 2),
      condition("総単位", "total", 3),
      condition("達成済み", "selective_group", 0),
    ],
    missingRequiredCourses: [
      {
        courseId: "r",
        name: "キャリア設計",
        credits: 4,
        classificationId: "social",
      },
      { courseId: "m", name: "線形代数", credits: 2, classificationId: "math" },
      { courseId: "u", name: "未分類科目", credits: 1, classificationId: null },
    ],
    recommendations: [
      {
        courseId: "e",
        name: "選択候補",
        credits: 2,
        offerings: [],
        status: "not_taken",
        contributions: [
          { requirementId: "選択条件" },
          { requirementId: "総単位" },
        ],
      },
      {
        courseId: "t",
        name: "総単位候補",
        credits: 3,
        offerings: [],
        status: "pending",
        contributions: [
          { requirementId: "総単位", reason: "総単位の不足を減らせます" },
        ],
      },
    ],
  };
  const i18n = createSiteI18n({ languages: ["ja"] });
  const html = renderToStaticMarkup(
    createElement(
      I18nextProvider,
      { i18n },
      createElement(ShortageCourses, { result }),
    ),
  );
  assert.match(html, /社会人基礎<\/h5>.*キャリア設計<\/span>.*4単位/);
  assert.match(html, /数理<\/h5>.*線形代数<\/span>.*2単位/);
  assert.match(
    html,
    /区分を確認できない必修科目<\/h5>.*未分類科目<\/span>.*1単位/,
  );
  assert.match(html, /選択条件/);
  assert.match(
    html,
    /<details class="shortage-candidates"><summary aria-label="選択条件の候補を見る">候補を見る<\/summary>/,
  );
  assert.match(html, /選択候補<\/span>.*2単位/);
  assert.match(html, /その他の履修候補.*総単位候補.*総単位の不足を減らせます/);
  assert.doesNotMatch(html, /<h4>総単位<\/h4>|<h4>区分の合計<\/h4>/);
  assert.equal((html.match(/選択候補<\/span>/g) ?? []).length, 1);
  assert.doesNotMatch(html, /達成済み/);
  assert.doesNotMatch(html, /あと\d+単位/);
});

test("必修や選択系に表示済みの科目はその他の候補に重複しない", () => {
  const result = {
    requirements: [
      { id: "total", kind: "total", shortage: 4 },
      { id: "category", kind: "classification_total", shortage: 4 },
      { id: "elective", kind: "elective_total", name: "選択条件", shortage: 2 },
    ],
    missingRequiredCourses: [
      { courseId: "r", name: "必修科目", credits: 2, classificationId: null },
    ],
    recommendations: [
      {
        courseId: "r",
        name: "必修科目",
        credits: 2,
        contributions: [{ requirementId: "total", reason: "必修" }],
      },
      {
        courseId: "e",
        name: "選択科目",
        credits: 2,
        contributions: [
          { requirementId: "total", reason: "総単位" },
          { requirementId: "elective", reason: "選択" },
        ],
      },
      {
        courseId: "c",
        name: "その他科目",
        credits: 2,
        contributions: [
          { requirementId: "total", reason: "総単位" },
          { requirementId: "category", reason: "区分" },
        ],
      },
    ],
  };
  const i18n = createSiteI18n({ languages: ["ja"] });
  const html = renderToStaticMarkup(
    createElement(
      I18nextProvider,
      { i18n },
      createElement(ShortageCourses, { result }),
    ),
  );
  assert.equal((html.match(/必修科目<\/span>/g) ?? []).length, 1);
  assert.equal((html.match(/選択科目<\/span>/g) ?? []).length, 1);
  assert.match(html, /その他の履修候補.*その他科目/);
});

test("選択必修が充足していても不足する内訳とその候補を親の下に表示する", () => {
  const result = {
    requirements: [
      {
        id: "group",
        kind: "selective_group",
        name: "人文・社会の選択必修",
        shortage: 0,
      },
      {
        id: "human",
        kind: "subminimum",
        name: "人文の内訳最低単位",
        shortage: 2,
        parentId: "group",
      },
      {
        id: "social",
        kind: "subminimum",
        name: "社会の内訳最低単位",
        shortage: 0,
        parentId: "group",
      },
    ],
    missingRequiredCourses: [],
    recommendations: [
      {
        courseId: "c",
        name: "哲学",
        credits: 2,
        offerings: [],
        status: "not_taken",
        contributions: [
          { requirementId: "human", reason: "人文の不足を減らせます" },
        ],
      },
    ],
  };
  const i18n = createSiteI18n({ languages: ["ja"] });
  const html = renderToStaticMarkup(
    createElement(
      I18nextProvider,
      { i18n },
      createElement(ShortageCourses, { result }),
    ),
  );
  assert.match(
    html,
    /選択必修<\/h4>.*人文・社会の選択必修.*人文<\/strong>.*哲学/,
  );
  assert.match(
    html,
    /<details class="shortage-candidates"><summary aria-label="人文の内訳最低単位の候補を見る">候補を見る<\/summary>/,
  );
  assert.doesNotMatch(html, /内訳の最低条件|社会の内訳最低単位|あと\d+単位/);
});
