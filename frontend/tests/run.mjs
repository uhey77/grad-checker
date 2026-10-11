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
      "--outDir",
      directory,
      "src/application/course-catalog/filterCourses.ts",
      "src/application/course-catalog/sortCourses.ts",
      "src/presentation/course-catalog/labels.ts",
      "src/application/course-catalog/CatalogUseCases.ts",
      "src/infrastructure/course-catalog/mappers.ts",
    ],
    { stdio: "inherit" },
  );
  if (compile.status !== 0) process.exitCode = compile.status ?? 1;
  else {
    const result = spawnSync(
      process.execPath,
      ["--test", "tests/course-catalog.test.mjs"],
      {
        stdio: "inherit",
        env: { ...process.env, CATALOG_TEST_BUILD_DIRECTORY: directory },
      },
    );
    process.exitCode = result.status ?? 1;
  }
} finally {
  await rm(directory, { recursive: true, force: true });
}
