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
      "src/modules/subjects/application/subject-list/filterSubjects.ts",
      "src/modules/subjects/application/subject-list/sortSubjects.ts",
      "src/components/subjects/labels.ts",
      "src/modules/subjects/application/subject-list/SubjectListUseCases.ts",
      "src/modules/subjects/infrastructure/subject-list/mappers.ts",
      "src/modules/subjects/infrastructure/subject-list/HttpSubjectListRepository.ts",
      "src/hooks/subjects/errors.ts",
      "src/modules/accounts/infrastructure/HttpAuthRepository.ts",
      "src/modules/profiles/infrastructure/HttpProfileRepository.ts",
      "src/modules/profiles/application/ProfileUseCases.ts",
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
