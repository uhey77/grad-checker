import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";

const { groupPrograms, selectablePrograms } = await import(
  pathToFileURL(
    join(
      process.env.SUBJECT_TEST_BUILD_DIRECTORY,
      "modules/profiles/public.js",
    ),
  )
);

test("実際の課程を学部と大学院に分け、大学の掲載順でまとめる", async () => {
  const load = async (name) =>
    JSON.parse(
      await readFile(
        new URL(`../../../backend/seeds/${name}`, import.meta.url),
        "utf8",
      ),
    );
  const [cs, university, requirements] = await Promise.all([
    load("cs_2026.json"),
    load("university_2026.json"),
    load("university_requirements_2026.json"),
  ]);
  const programs = new Map(
    [...cs.academic_programs, ...university.academic_programs].map((p) => [
      p.id,
      p,
    ]),
  );
  const policies = new Map(
    requirements.completion_policies.map((p) => [p.curriculum_id, p]),
  );
  const options = [...cs.curricula, ...university.curricula]
    .map((c) => {
      const p = programs.get(c.program_id),
        policy = policies.get(c.id);
      return {
        curriculumId: c.id,
        curriculumName: c.name,
        facultyName: p.faculty_name,
        departmentName: p.department_name,
        specializationName: p.specialization_name,
        courseName: p.course_name,
        completionPolicy: policy
          ? {
              degreeLevel: policy.degree_level,
              unresolvedReasons: policy.unresolved_reasons,
            }
          : undefined,
      };
    })
    .reverse();
  const snapshot = [...options];
  const grouped = groupPrograms(options);
  assert.deepEqual(options, snapshot);
  assert.equal(grouped.undergraduate.length, 25);
  assert.equal(grouped.graduate.length, 13);
  assert.equal(grouped.other.length, 0);
  const selectable = selectablePrograms(options);
  assert.equal(selectable.length, 31);
  assert.equal(groupPrograms(selectable).graduate.length, 6);
  assert.ok(
    selectable.every((p) => !p.completionPolicy?.unresolvedReasons.length),
  );
  assert.equal(
    new Set(
      [...grouped.undergraduate, ...grouped.graduate].map(
        (p) => p.curriculumId,
      ),
    ).size,
    38,
  );
  assert.deepEqual(
    [...new Set(grouped.undergraduate.map((p) => p.facultyName))],
    [
      "コンピュータサイエンス学部",
      "メディア学部",
      "工学部",
      "応用生物学部",
      "デザイン学部",
      "医療保健学部",
    ],
  );
  assert.deepEqual(
    [...new Set(grouped.graduate.map((p) => p.facultyName))],
    [
      "バイオ・情報メディア研究科",
      "工学研究科",
      "デザイン研究科",
      "医療技術学研究科",
    ],
  );
  assert.deepEqual(
    grouped.undergraduate
      .filter((p) => p.specializationName === "先進情報専攻")
      .map((p) => p.courseName),
    ["情報基盤コース", "人間情報コース", "人工知能コース"],
  );
  assert.deepEqual(
    grouped.graduate
      .filter((p) => p.specializationName === "バイオニクス専攻")
      .map((p) => p.courseName),
    ["修士課程", "修士課程（英語プログラム）", "博士後期課程"],
  );
});

test("判定情報がない所属も失わず、分類不能な所属はその他へ分ける", () => {
  const option = (id, faculty) => ({
    curriculumId: id,
    curriculumName: id,
    facultyName: faculty,
    departmentName: null,
    specializationName: null,
    courseName: null,
  });
  const grouped = groupPrograms([
    option("unknown", "新しい教育組織"),
    option("grad", "新研究科"),
    option("faculty", "新学部"),
  ]);
  assert.deepEqual(
    grouped.undergraduate.map((p) => p.curriculumId),
    ["faculty"],
  );
  assert.deepEqual(
    grouped.graduate.map((p) => p.curriculumId),
    ["grad"],
  );
  assert.deepEqual(
    grouped.other.map((p) => p.curriculumId),
    ["unknown"],
  );
  const programs = [
    option("legacy", "新学部"),
    {
      ...option("pending", "新研究科"),
      completionPolicy: { unresolvedReasons: ["条件の確認中"] },
    },
  ];
  assert.deepEqual(
    selectablePrograms(programs).map((p) => p.curriculumId),
    ["legacy"],
  );
  assert.equal(programs.length, 2);
});
