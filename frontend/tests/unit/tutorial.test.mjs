import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const { completeTutorial, tutorialCompleted } = await import(
  pathToFileURL(
    join(
      process.env.SUBJECT_TEST_BUILD_DIRECTORY,
      "apps/web/pages/tutorial/tutorialProgress.js",
    ),
  )
);

test("練習の終了状態はブラウザー上でアカウントごとに保持する", () => {
  const values = new Map();
  globalThis.window = {
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
    },
  };
  assert.equal(tutorialCompleted("first"), false);
  completeTutorial("first");
  assert.equal(tutorialCompleted("first"), true);
  assert.equal(tutorialCompleted("second"), false);
  delete globalThis.window;
});

test("ストレージが使えない場合も練習を終了できる", () => {
  globalThis.window = {
    get localStorage() {
      throw new Error("disabled");
    },
  };
  assert.equal(tutorialCompleted("first"), false);
  assert.doesNotThrow(() => completeTutorial("first"));
  delete globalThis.window;
});
