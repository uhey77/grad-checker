import assert from "node:assert/strict";
import test from "node:test";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { JSDOM } from "jsdom";
import { act, createElement } from "react";
import { createRoot } from "react-dom/client";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;
const load = (path) => import(pathToFileURL(join(directory, path)));
const { parseGradeScreenshotText, approximateMatch } = await load(
  "modules/grades/application/services/gradeScreenshot.js",
);
const { planGradeImport } = await load(
  "modules/grades/application/services/gradeDraft.js",
);
const { ReadGradeScreenshotUseCase, GradeScreenshotError } = await load(
  "modules/grades/public.js",
);
const { useGradeScreenshot } = await load(
  "apps/web/hooks/grades/useGradeScreenshot.js",
);
const { useGradeEntry } = await load("apps/web/hooks/grades/useGradeEntry.js");

const courses = [
  ["society", "社会学"],
  ["math", "数学概論"],
  ["rw1", "English RWⅠ"],
  ["rw2", "English RWⅡ"],
  ["adv1", "Advanced EnglishⅠ"],
  ["adv2", "Advanced EnglishⅡ"],
  ["coop1", "コーオプ実習Ⅰ"],
  ["coop2", "コーオプ実習Ⅱ"],
  ["abroad", "海外研修Ⅰ"],
  ["seminar", "先進情報専門演習・人間Ⅰ"],
  ["info-society", "情報社会学"],
]
  .map(([courseId, name]) => ({ courseId, name, inCurriculum: true }))
  .concat(
    // 他学部が開講する同名・課程外の科目。
    [
      ["society-other", "社会学"],
      ["astronomy-a", "天文の世界"],
      ["astronomy-b", "天文の世界"],
      ["design", "建築文化論"],
    ].map(([courseId, name]) => ({ courseId, name, inCurriculum: false })),
  );

// tesseract.jsで読み取った実際の出力の傾向（文字間の空白、Ⅰ→|、Ⅱ→ll、番号の欠落、誤読）を再現する。
const ocrText = [
  "科目 コー ド 科目 名 単位 評価 年 度 学期",
  "40C4070 社会 学 2 B 2024 後期",
  "85B7902 数 学 根 論 2 S 2024 後 期",
  "48E6243 English RW | 1 b 2025 前 其",
  "62B4269 Advanced English ll 1 C 2025 前 期",
  "83B5564 コー オブ 実習 3 A 2024 後期",
  "16E2861 海外 研修 | 1 X 2024 後期",
  "49A2261 ミー マ シ イシ タニ ー ラ ェ イ ス 2 D 2024 前 期",
  "11A0001 情報 社会 学 2 履修中 2025 後期",
  "",
  "合計 18",
].join("\n");

test("あいまい一致は部分文字列の編集距離と位置を返す", () => {
  assert.deepEqual(approximateMatch("数学概論", "85b7902数学根論2s"), {
    distance: 1,
    start: 7,
    end: 11,
  });
  assert.equal(approximateMatch("", "abc"), null);
});

test("OCRの空白・番号の読み違いを吸収して科目と評価・年度・学期を読み取る", () => {
  const rows = parseGradeScreenshotText(ocrText, courses);
  const byLine = (fragment) => rows.find((row) => row.line.includes(fragment));
  // 見出し・合計行は成績の行として扱わない。
  assert.equal(rows.length, 8);
  assert.equal(byLine("科目 名"), undefined);

  assert.deepEqual(byLine("社会 学"), {
    line: "40C4070 社会 学 2 B 2024 後期",
    candidateCourseIds: ["society"],
    courseId: "society",
    needsReview: false,
    resultStatus: "finalized",
    gradeCode: "B",
    academicYear: 2024,
    termCode: "second",
  });
  // 1文字の読み違いは補正するが、本人の確認を求める。
  const math = byLine("数 学");
  assert.equal(math.courseId, "math");
  assert.equal(math.needsReview, true);
  assert.equal(math.gradeCode, "S");
  // 「|」をⅠ、「ll」をⅡと推定し、小文字の評価と学期の誤読も読み取る。
  const rw = byLine("English RW");
  assert.deepEqual(rw.candidateCourseIds, ["rw1", "rw2"]);
  assert.equal(rw.courseId, "rw1");
  assert.equal(rw.needsReview, true);
  assert.equal(rw.gradeCode, "B");
  assert.equal(rw.termCode, "first");
  assert.equal(byLine("Advanced").courseId, "adv2");
  // 番号を読み取れない場合は候補だけを示し、本人に選んでもらう。
  const coop = byLine("コー オブ");
  assert.deepEqual(coop.candidateCourseIds, ["coop1", "coop2"]);
  assert.equal(coop.courseId, null);
  assert.equal(coop.gradeCode, "A");
  // 番号違いの科目がなければ、そのまま選ぶ。単位数の1を番号として扱わない。
  const abroad = byLine("海外 研修");
  assert.equal(abroad.courseId, "abroad");
  assert.equal(abroad.gradeCode, "X");
  // 照合できなくても評価がある行は表示し、反映対象にはしない。
  const unknown = byLine("ミー マ");
  assert.deepEqual(unknown.candidateCourseIds, []);
  assert.equal(unknown.courseId, null);
  assert.equal(unknown.gradeCode, "D");
  // 短い科目名より、一致した文字数が多い科目を優先する。履修中は未確定とする。
  const pending = byLine("情報 社会 学");
  assert.equal(pending.courseId, "info-society");
  assert.equal(pending.resultStatus, "pending");
  assert.equal(pending.gradeCode, null);
  assert.equal(pending.academicYear, 2025);
});

test("本人課程の科目を優先し、課程外の同名科目は推測で選ばない", () => {
  const rows = parseGradeScreenshotText(
    "社会 学 2 B 2024 後期\n天文 の 世界 2 A 2024 前期\n建築 文化 論 2 C 2024 前期",
    courses,
  );
  assert.deepEqual(rows[0].candidateCourseIds, ["society"]);
  assert.equal(rows[0].courseId, "society");
  assert.deepEqual(rows[1].candidateCourseIds, ["astronomy-a", "astronomy-b"]);
  assert.equal(rows[1].courseId, null);
  assert.equal(rows[1].needsReview, true);
  assert.equal(rows[2].courseId, "design");
});

test("短い科目名は完全一致だけを照合し、科目コード内の数字を年度にしない", () => {
  const rows = parseGradeScreenshotText(
    "AB2024 社 会 字 2 A\n社会学 A2024 2025年度 春学期",
    courses,
  );
  assert.equal(rows[0].courseId, null);
  assert.equal(rows[0].academicYear, null);
  assert.equal(rows[1].courseId, "society");
  assert.equal(rows[1].academicYear, 2025);
  assert.equal(rows[1].termCode, "first");
});

const attempt = (courseId, attemptNo, gradeCode, academicYear, termCode) => ({
  courseId,
  attemptNo,
  resultStatus: gradeCode ? "finalized" : "pending",
  gradeCode,
  academicYear,
  termCode,
});
const imported = (courseId, gradeCode, academicYear, termCode) => ({
  courseId,
  resultStatus: gradeCode ? "finalized" : "pending",
  gradeCode,
  academicYear,
  termCode,
});

test("読み取った成績を時期順の回次に統合し、反映内容を科目ごとに返す", () => {
  const draft = [
    attempt("a", 1, "D", 2024, "first"),
    attempt("b", 1, "A", 2024, "second"),
    attempt("c", 1, "B", null, null),
    attempt("e", 1, "S", 2024, "first"),
  ];
  const plan = planGradeImport(draft, [
    // 既存の不合格の後の再履修として追加する。
    imported("a", "B", 2025, "first"),
    // 同じ時期の回次は置き換え、同じ内容なら変更なしとする。
    imported("b", "A", 2024, "second"),
    // 時期が不明な既存の回次は読み取った成績で置き換える。
    imported("c", "C", 2025, "second"),
    // 同じ時期の重複行は後の行を使う。
    imported("d", "D", 2025, "first"),
    imported("d", "X", 2025, "first"),
    // 合格の後に別の成績がある科目は回次の規則に反するため変更しない。
    imported("e", "A", 2025, "first"),
  ]);
  assert.deepEqual(Object.fromEntries(plan.outcomes), {
    a: "updated",
    b: "unchanged",
    c: "updated",
    d: "added",
    e: "invalid",
  });
  assert.deepEqual(
    plan.grades.filter((g) => g.courseId === "a"),
    [attempt("a", 1, "D", 2024, "first"), attempt("a", 2, "B", 2025, "first")],
  );
  assert.deepEqual(
    plan.grades.filter((g) => g.courseId === "c"),
    [attempt("c", 1, "C", 2025, "second")],
  );
  assert.deepEqual(
    plan.grades.filter((g) => g.courseId === "d"),
    [attempt("d", 1, "X", 2025, "first")],
  );
  assert.deepEqual(
    plan.grades.filter((g) => g.courseId === "e"),
    [attempt("e", 1, "S", 2024, "first")],
  );
  // 元の配列は変更しない。
  assert.equal(draft.length, 4);
});

test("画像以外・大きすぎる画像・成績の行がない画像を業務エラーにする", async () => {
  const calls = [];
  const reader = {
    read: async (image, signal, onProgress) => {
      calls.push({ image, signal });
      onProgress?.({ stage: "recognizing", ratio: 0.5 });
      return image.text();
    },
  };
  const useCase = new ReadGradeScreenshotUseCase(reader);
  const signal = new AbortController().signal;
  const problem = async (blob) =>
    useCase.execute(blob, courses, signal).then(
      () => null,
      (error) => {
        assert.ok(error instanceof GradeScreenshotError);
        return error.problem;
      },
    );
  assert.equal(
    await problem(new Blob(["x"], { type: "text/plain" })),
    "not_image",
  );
  assert.equal(
    await problem(
      new Blob([new Uint8Array(20 * 1024 * 1024 + 1)], { type: "image/png" }),
    ),
    "too_large",
  );
  assert.equal(
    await problem(new Blob(["見出しだけ"], { type: "image/png" })),
    "no_rows",
  );
  assert.equal(calls.length, 1);
  const progress = [];
  const rows = await useCase.execute(
    new Blob(["社会学 A 2024 前期"], { type: "image/png" }),
    courses,
    signal,
    (value) => progress.push(value),
  );
  assert.equal(rows[0].courseId, "society");
  assert.equal(calls[1].signal, signal);
  assert.deepEqual(progress, [{ stage: "recognizing", ratio: 0.5 }]);
});

async function setup(t, readScreenshot) {
  const dom = new JSDOM('<div id="root"></div>', { url: "http://localhost" });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  let current;
  const catalog = {
    getCatalog: {
      execute: async () => ({ courses: [], categories: [] }),
    },
  };
  const grades = {
    getGrades: {
      execute: async () => ({
        dataRevision: 1,
        grades: [attempt("rw1", 1, "D", 2024, "first")],
      }),
    },
    saveGrades: { execute: async () => assert.fail("保存しない") },
    readScreenshot,
  };
  // 再描画で読み込みが繰り返されないよう、Hookへ渡す関数は固定する。
  const ignore = () => {};
  function Harness() {
    const entry = useGradeEntry(catalog, grades, "csrf", ignore, 1, ignore);
    const screenshot = useGradeScreenshot(
      grades,
      courses,
      entry.draft,
      entry.applyImport,
    );
    current = { entry, screenshot };
    return null;
  }
  const root = createRoot(globalThis.document.getElementById("root"));
  await act(async () => root.render(createElement(Harness)));
  t.after(async () => {
    await act(async () => root.unmount());
    dom.window.close();
    delete globalThis.window;
    delete globalThis.document;
    delete globalThis.IS_REACT_ACT_ENVIRONMENT;
  });
  return {
    get current() {
      return current;
    },
  };
}

test("読み取り結果を確認し、選んだ行だけを未保存の成績へ反映する", async (t) => {
  const rows = parseGradeScreenshotText(
    [
      "English RW | 1 B 2025 前期",
      "コー オブ 実習 3 A 2024 後期",
      "ミー マ シ 2 D 2024 前期",
      "社会 学 2 C 2024 後期",
    ].join("\n"),
    courses,
  );
  const h = await setup(t, { execute: async () => rows });
  await act(async () => h.current.screenshot.read(new Blob()));
  const review = h.current.screenshot.rows;
  // 科目と評価が揃った行だけを初期選択し、既存の不合格の後の再履修として示す。
  assert.deepEqual(
    review.map((row) => [row.selected, row.outcome]),
    [
      [true, "updated"],
      [false, null],
      [false, null],
      [true, "added"],
    ],
  );
  assert.equal(h.current.screenshot.selectedCount, 2);
  // 番号を判別できない行は科目を選ぶと反映対象になる。照合できない行は選べない。
  await act(async () => h.current.screenshot.chooseCourse(1, "coop2"));
  await act(async () => h.current.screenshot.toggle(2, true));
  await act(async () => h.current.screenshot.toggle(3, false));
  assert.equal(h.current.screenshot.selectedCount, 2);
  await act(async () => h.current.screenshot.apply());
  assert.equal(h.current.screenshot.rows, null);
  assert.equal(h.current.entry.dirty, true);
  assert.match(
    h.current.entry.notice,
    /スクリーンショットの成績を反映しました/,
  );
  assert.deepEqual(h.current.entry.draft, [
    attempt("coop2", 1, "A", 2024, "second"),
    attempt("rw1", 1, "D", 2024, "first"),
    attempt("rw1", 2, "B", 2025, "first"),
  ]);
});

test("読み取りの中止・失敗では結果を表示せず、失敗の理由を表示する", async (t) => {
  let release;
  let attempt = 0;
  const h = await setup(t, {
    execute: (_image, _courses, signal) => {
      attempt++;
      if (attempt === 2)
        return Promise.reject(new GradeScreenshotError("no_rows"));
      return new Promise((resolve) => {
        release = () => resolve([]);
        signal.addEventListener("abort", () => resolve([]));
      });
    },
  });
  await act(async () => h.current.screenshot.read(new Blob()));
  assert.equal(h.current.screenshot.reading, true);
  await act(async () => h.current.screenshot.cancel());
  release();
  assert.equal(h.current.screenshot.reading, false);
  assert.equal(h.current.screenshot.rows, null);
  assert.equal(h.current.screenshot.error, "");
  await act(async () => h.current.screenshot.read(new Blob()));
  assert.equal(h.current.screenshot.rows, null);
  assert.match(h.current.screenshot.error, /成績の行を読み取れませんでした/);
});
