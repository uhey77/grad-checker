import assert from "node:assert/strict";
import test from "node:test";
import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { I18nextProvider } from "react-i18next";
import ts from "typescript";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;
const built = (file) => import(pathToFileURL(join(directory, file)));
const { createSiteI18n, initialLanguage, languageStorageKey } =
  await built("i18n/createI18n.js");
const { english } = await built("i18n/en.js");
const { translateMessage } = await built("i18n/messages.js");
const { offeringLabels } = await built(
  "apps/web/components/subjects/labels.js",
);
const { AuthForm } = await built("apps/web/components/accounts/AuthForm.js");
const { ProgramCoverage } = await built(
  "apps/web/components/profiles/ProgramCoverage.js",
);
const { GraduationResultView } = await built(
  "apps/web/components/requirements/GraduationResultView.js",
);
const { ErrorState, FormError } = await built(
  "apps/web/components/StatusPanels.js",
);
const { SaveBar } = await built("apps/web/components/SaveBar.js");
const { GradeTable } = await built("apps/web/components/grades/GradeTable.js");

test("保存済みの選択、ブラウザーの優先言語、日本語フォールバックの順で初期言語を決める", () => {
  assert.equal(initialLanguage("ja", ["en-US"]), "ja");
  assert.equal(initialLanguage("en", ["ja-JP"]), "en");
  assert.equal(initialLanguage(null, ["en-US", "ja"]), "en");
  assert.equal(initialLanguage(null, ["ja-JP", "en"]), "ja");
  assert.equal(initialLanguage("invalid", ["fr-FR", "en-GB"]), "en");
  assert.equal(initialLanguage(null, ["fr-FR"]), "ja");
  assert.equal(initialLanguage(null, []), "ja");
});

test("切替で言語だけを保存してhtml.langとタイトルを更新し、再起動時にも復元する", async () => {
  const values = new Map();
  const writes = [];
  const storage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => {
      values.set(key, value);
      writes.push([key, value]);
    },
  };
  const page = { documentElement: { lang: "" }, title: "" };
  const i18n = createSiteI18n({ storage, languages: ["en-US"], page });
  assert.equal(page.documentElement.lang, "en");
  assert.equal(page.title, "Graduation Requirements Checker");
  assert.deepEqual(writes, []);
  await i18n.changeLanguage("ja");
  assert.equal(page.documentElement.lang, "ja");
  assert.equal(page.title, "卒業要件チェッカー");
  assert.deepEqual(writes, [[languageStorageKey, "ja"]]);
  assert.equal(
    createSiteI18n({ storage, languages: ["en"] }).resolvedLanguage,
    "ja",
  );
});

test("ブラウザーストレージの読取り・書込みが禁止されても起動と切替ができる", async () => {
  const storage = {
    getItem() {
      throw new Error("blocked");
    },
    setItem() {
      throw new Error("blocked");
    },
  };
  const i18n = createSiteI18n({ storage, languages: ["en"] });
  assert.equal(i18n.t("ログイン"), "Log in");
  await i18n.changeLanguage("ja");
  assert.equal(i18n.t("ログイン"), "ログイン");
});

test("全翻訳の変数が日本語と英語で一致し、全画面の静的キーとAPIの既知エラーに訳がある", async () => {
  const variables = (value) =>
    [...value.matchAll(/{{\s*(\w+)\s*}}/g)].map((m) => m[1]).sort();
  for (const [key, value] of Object.entries(english)) {
    assert.ok(value.trim(), key);
    assert.deepEqual(variables(key), variables(value), key);
  }
  async function scan(path) {
    for (const entry of await readdir(path, { withFileTypes: true })) {
      const file = join(path, entry.name);
      if (entry.isDirectory()) {
        if (entry.name !== "i18n") await scan(file);
        continue;
      }
      if (!/\.tsx?$/.test(file)) continue;
      const ast = ts.createSourceFile(
        file,
        await readFile(file, "utf8"),
        ts.ScriptTarget.Latest,
        true,
      );
      function visit(node) {
        if (
          ts.isCallExpression(node) &&
          ts.isIdentifier(node.expression) &&
          node.expression.text === "t" &&
          ts.isStringLiteral(node.arguments[0])
        )
          assert.ok(
            Object.hasOwn(english, node.arguments[0].text),
            `${file}: ${node.arguments[0].text}`,
          );
        if (
          ts.isJsxAttribute(node) &&
          node.name.getText(ast) === "i18nKey" &&
          ts.isStringLiteral(node.initializer)
        )
          assert.ok(
            Object.hasOwn(english, node.initializer.text),
            `${file}: ${node.initializer.text}`,
          );
        // Infrastructure and hook failures stay in the source language until rendering.
        if (
          !file.endsWith(".tsx") &&
          ts.isStringLiteral(node) &&
          /[ぁ-んァ-ヶ一-龯].*。$/.test(node.text)
        )
          assert.ok(Object.hasOwn(english, node.text), `${file}: ${node.text}`);
        ts.forEachChild(node, visit);
      }
      visit(ast);
    }
  }
  await scan("src");
  const contract = JSON.parse(
    await readFile(
      "../backend/apps/api/controllers/apidocs/openapi.json",
      "utf8",
    ),
  );
  function checkDetails(value) {
    if (!value || typeof value !== "object") return;
    if (typeof value.detail === "string")
      assert.ok(Object.hasOwn(english, value.detail), value.detail);
    for (const item of Object.values(value)) checkDetails(item);
  }
  checkDetails(contract);
});

test("表示済みの検証エラーも選択言語で再表示し、未知のdetailや入力された科目名は原文を保持する", async () => {
  const i18n = createSiteI18n({ languages: ["en"] });
  const render = (component, props) =>
    renderToStaticMarkup(
      createElement(I18nextProvider, { i18n }, createElement(component, props)),
    );
  const message = "パスワードは12〜128文字で入力してください。";
  assert.match(
    render(FormError, { children: message }),
    /Use 12–128 characters/,
  );
  assert.match(
    render(ErrorState, {
      message: "ユーザー名またはパスワードを確認してください。",
      actionLabel: "再試行",
      onAction() {},
    }),
    /Check your username or password/,
  );
  assert.equal(
    translateMessage("履修年度は1900〜2100の整数で入力してください。", i18n.t),
    "Enter an integer from 1900 to 2100 for the academic year.",
  );
  assert.equal(
    translateMessage("未知のエラー詳細。", i18n.t),
    "未知のエラー詳細。",
  );
  assert.match(
    render(SaveBar, {
      notice: "成績を保存しました。",
      error: "",
      busy: false,
      dirty: false,
      cleanStatus: "",
      actions: null,
    }),
    /Grades saved/,
  );
  await i18n.changeLanguage("ja");
  assert.match(
    render(FormError, { children: message }),
    /パスワードは12〜128文字/,
  );
});

test("英語の入力フォーム・成績・課程の対応状況を表示し、公式データを維持する", () => {
  const i18n = createSiteI18n({ languages: ["en"] });
  const render = (component, props) =>
    renderToStaticMarkup(
      createElement(I18nextProvider, { i18n }, createElement(component, props)),
    );
  const form = render(AuthForm, {
    mode: "register",
    policy: { passwordMinLength: 12, passwordMaxLength: 128 },
    busy: false,
    submit() {},
  });
  assert.match(form, /Confirm password/);
  assert.match(form, /Use 12–128 characters/);
  const coverage = render(ProgramCoverage, {
    program: {
      verificationStatus: "unverified",
      sourceDocument: "https://example.com/official.pdf",
      sourcePages: "p.12",
      completionPolicy: null,
    },
  });
  assert.equal(coverage, "");
  const unavailable = render(ProgramCoverage, {
    program: {
      completionPolicy: {
        campus: "hachioji",
        degreeLevel: "master",
        catalogStatus: "verified",
        requirementsStatus: "verified",
        rulesStatus: "unverified",
        unresolvedReasons: ["公式規則の未確認理由"],
      },
    },
  });
  assert.match(unavailable, /Evaluation is unavailable/);
  assert.match(unavailable, /公式規則の未確認理由/);
  const course = {
    courseId: "c1",
    name: "日本語の公式科目名 <script>",
    code: "CS001",
    credits: 2,
    offerings: [],
    placement: null,
    offeringFacultyName: "公式学部名",
    offeringDepartmentName: null,
    offeringSpecializationName: null,
    teachingTypeLabel: "講義",
  };
  const grades = render(GradeTable, {
    courses: [course],
    draft: [
      {
        courseId: "c1",
        attemptNo: 1,
        gradeCode: "D",
        resultStatus: "finalized",
        academicYear: 2026,
        termCode: "first",
      },
    ],
    saved: [],
    disabled: false,
    resetFilters() {},
    choose() {},
    setPeriod() {},
    addRetake() {},
    removeLatest() {},
  });
  assert.match(grades, /D \(failed\)/);
  assert.match(grades, /First term/);
  assert.match(grades, /日本語の公式科目名 &lt;script&gt;/);
  assert.match(grades, /公式学部名/);
  assert.doesNotMatch(grades, /<script>/);
});

test("英語でも判定保留と出典・推薦の原文を保ち、開講期を選択言語で表示する", (context) => {
  globalThis.window = { matchMedia: () => ({ matches: true }) };
  context.after(() => {
    delete globalThis.window;
  });
  const i18n = createSiteI18n({ languages: ["en"] });
  const result = {
    result: "pending",
    degreeLevel: "master",
    curriculum: { id: "test" },
    dataRevision: 1,
    evaluatedAt: "2026-10-20T10:20:30Z",
    total: {
      creditedCredits: 2,
      requiredCredits: 30,
      earnedCredits: 2,
      shortage: 28,
      result: "fail",
    },
    requirements: [],
    externalAllocations: [],
    allocations: [],
    missingRequiredCourses: [],
    recommendations: null,
    warnings: [],
    completionConditions: [
      {
        code: "thesis",
        name: "学位論文の審査",
        status: "unknown",
        sourceDocument: "https://example.com/rules.pdf",
        sourcePages: "p.10",
      },
    ],
  };
  const markup = renderToStaticMarkup(
    createElement(
      I18nextProvider,
      { i18n },
      createElement(GraduationResultView, { result }),
    ),
  );
  assert.match(markup, /Degree completion requirements/);
  assert.match(markup, /Pending/);
  assert.match(markup, /Unverified \/ pending/);
  assert.match(markup, /学位論文の審査/);
  assert.match(markup, /href="https:\/\/example.com\/rules.pdf"/);
  const recommendation = {
    courseId: "recommended",
    name: "公式の推薦科目名",
    credits: 2,
    offerings: [],
    status: "not_taken",
    isRequired: true,
    contributions: [
      {
        requirementId: "r",
        code: "R1",
        reason: "原文の推薦理由",
        name: "公式の条件名",
        shortageReduction: 2,
      },
    ],
  };
  const recommended = renderToStaticMarkup(
    createElement(
      I18nextProvider,
      { i18n },
      createElement(GraduationResultView, {
        result: {
          ...result,
          degreeLevel: "bachelor",
          recommendations: [recommendation],
        },
      }),
    ),
  );
  assert.match(recommended, /Recommended courses/);
  assert.match(recommended, /公式の推薦科目名/);
  assert.match(recommended, /原文の推薦理由/);
  assert.match(recommended, /Not taken/);
  const offerings = [
    { semesterOrder: 1, termCode: "first" },
    { semesterOrder: 2, termCode: "second" },
  ];
  assert.deepEqual(offeringLabels(offerings, i18n.t), [
    "Year 1: First term, Second term",
  ]);
  assert.deepEqual(offeringLabels(offerings), ["1年次前期・後期"]);
});
