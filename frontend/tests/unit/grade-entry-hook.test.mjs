import assert from "node:assert/strict";
import test from "node:test";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { JSDOM } from "jsdom";
import { act, createElement } from "react";
import { createRoot } from "react-dom/client";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;
const load = (file) => import(pathToFileURL(join(directory, file)));
const { useGradeEntry } = await load("apps/web/hooks/grades/useGradeEntry.js");
const { GradeError } = await load("modules/grades/public.js");

async function setup(t) {
  const dom = new JSDOM('<div id="root"></div>', { url: "http://localhost" });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  let current;
  let revision = 1;
  let saved = { dataRevision: 1, grades: [] };
  let loads = 0;
  let saveFailure = null;
  const catalog = { getCatalog: { execute: async () => ({ courses: [] }) } };
  const grades = {
    getGrades: {
      execute: async () => {
        loads++;
        return saved;
      },
    },
    saveGrades: {
      execute: async ({ expectedRevision, grades }) => {
        if (saveFailure) throw saveFailure;
        assert.equal(expectedRevision, saved.dataRevision);
        saved = { dataRevision: expectedRevision + 1, grades };
        return saved;
      },
    },
  };
  const expire = () => {};
  const reportRevision = () => {};
  function Harness() {
    current = useGradeEntry(
      catalog,
      grades,
      "csrf",
      expire,
      revision,
      reportRevision,
    );
    return null;
  }
  const root = createRoot(globalThis.document.getElementById("root"));
  const render = async () =>
    act(async () => root.render(createElement(Harness)));
  await render();
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
    get loads() {
      return loads;
    },
    setSaved(value) {
      saved = value;
    },
    failSave(value) {
      saveFailure = value;
    },
    async setRevision(value) {
      revision = value;
      await render();
    },
  };
}

test("未保存の成績は外部更新で上書きされず、確認後に再取得する", async (t) => {
  const h = await setup(t);
  await act(async () => h.current.choose("c1", 1, "A"));
  assert.equal(h.current.dirty, true);
  h.setSaved({ dataRevision: 2, grades: [] });
  await h.setRevision(2);
  assert.equal(h.loads, 1);
  assert.equal(h.current.draft[0].gradeCode, "A");
  await act(async () => h.current.retry());
  assert.equal(h.current.confirmReload, true);
  await act(async () => h.current.confirmRetry());
  assert.equal(h.loads, 2);
  assert.equal(h.current.dirty, false);
  assert.deepEqual(h.current.draft, []);
});

test("保存競合では編集を保持し、再取得で最新の版に戻す", async (t) => {
  const h = await setup(t);
  await act(async () => h.current.choose("c1", 1, "B"));
  h.failSave(new GradeError(409, "競合しました"));
  await act(async () => h.current.save());
  assert.equal(h.current.conflict, true);
  assert.equal(h.current.draft[0].gradeCode, "B");
  h.setSaved({ dataRevision: 2, grades: [] });
  await act(async () => h.current.retry());
  assert.equal(h.current.confirmReload, true);
  await act(async () => h.current.confirmRetry());
  assert.equal(h.current.conflict, false);
  assert.equal(h.current.data.saved.dataRevision, 2);
  assert.deepEqual(h.current.draft, []);
});

test("未保存の変更がなければ外部更新を自動で読み直す", async (t) => {
  const h = await setup(t);
  h.setSaved({ dataRevision: 2, grades: [] });
  await h.setRevision(2);
  assert.equal(h.loads, 2);
  assert.equal(h.current.data.saved.dataRevision, 2);
});

test("成績を保存し、全消去には確認を求める", async (t) => {
  const h = await setup(t);
  await act(async () => h.current.choose("c1", 1, "A"));
  await act(async () => h.current.save());
  assert.equal(h.current.dirty, false);
  assert.equal(h.current.data.saved.dataRevision, 2);
  await act(async () => h.current.choose("c1", 1, ""));
  await act(async () => h.current.save());
  assert.equal(h.current.confirmClear, true);
  assert.equal(h.current.data.saved.dataRevision, 2);
  await act(async () => h.current.save());
  assert.equal(h.current.confirmClear, false);
  assert.equal(h.current.data.saved.dataRevision, 3);
  assert.deepEqual(h.current.data.saved.grades, []);
});
