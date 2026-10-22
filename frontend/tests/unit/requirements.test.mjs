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
