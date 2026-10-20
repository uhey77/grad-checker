import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const directory = await mkdtemp(join(tmpdir(), "grad-checker-tests-"));
try {
  await writeFile(join(directory, "package.json"), '{"type":"module"}');
  const compile = spawnSync(
    process.execPath,
    [
      "node_modules/typescript/bin/tsc",
      "--ignoreConfig",
      "--target",
      "ES2022",
      "--module",
      "ESNext",
      "--moduleResolution",
      "Bundler",
      "--strict",
      "--skipLibCheck",
      "--rootDir",
      "src",
      "--rewriteRelativeImportExtensions",
      "--outDir",
      directory,
      "src/modules/accounts/public.ts",
      "src/modules/accounts/composition.ts",
      "src/modules/profiles/public.ts",
      "src/modules/profiles/composition.ts",
      "src/modules/grades/public.ts",
      "src/modules/grades/composition.ts",
      "src/modules/requirements/public.ts",
      "src/modules/requirements/composition.ts",
      "src/modules/subjects/public.ts",
      "src/modules/subjects/composition.ts",
      "src/components/subjects/labels.ts",
      "src/hooks/subjects/errors.ts",
      "src/hooks/grades/errors.ts",
    ],
    { stdio: "inherit" },
  );
  if (compile.status !== 0) process.exitCode = compile.status ?? 1;
  else {
    const result = spawnSync(
      process.execPath,
      [
        "--test",
        "tests/subject-list.test.mjs",
        "tests/architecture.test.mjs",
        "tests/accounts.test.mjs",
        "tests/profiles.test.mjs",
        "tests/grades.test.mjs",
        "tests/requirements.test.mjs",
        "tests/course-catalog.test.mjs",
        "tests/shared-http.test.mjs",
      ],
      {
        stdio: "inherit",
        env: { ...process.env, SUBJECT_TEST_BUILD_DIRECTORY: directory },
      },
    );
    process.exitCode = result.status ?? 1;
  }
} finally {
  await rm(directory, { recursive: true, force: true });
}
