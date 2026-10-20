import { mkdtemp, rm, writeFile, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const directory = await mkdtemp(join(tmpdir(), "grad-checker-tests-"));
try {
  await writeFile(join(directory, "package.json"), '{"type":"module"}');
  await symlink(
    resolve("node_modules"),
    join(directory, "node_modules"),
    process.platform === "win32" ? "junction" : "dir",
  );
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
      "--jsx",
      "react-jsx",
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
      "src/modules/grades/infrastructure/HttpGradeRepository.ts",
      "src/modules/grades/application/gradeDraft.ts",
      "src/modules/requirements/infrastructure/HttpGraduationRepository.ts",
      "src/modules/requirements/application/GraduationUseCases.ts",
      "src/modules/requirements/application/filterRequirements.ts",
      "src/modules/subjects/infrastructure/course-catalog/HttpCourseCatalogRepository.ts",
      "src/modules/subjects/application/course-catalog/CourseCatalogUseCases.ts",
      "src/modules/subjects/application/course-catalog/filterCatalogCourses.ts",
      "src/shared/infrastructure/http.ts",
      "src/shared/infrastructure/dtoReader.ts",
      "src/i18n/createI18n.ts",
      "src/i18n/messages.ts",
      "src/components/accounts/AuthForm.tsx",
      "src/components/requirements/GraduationResultView.tsx",
      "src/components/requirements/GraduationCheckPanel.tsx",
      "src/components/profiles/ProgramCoverage.tsx",
      "src/components/grades/GradeTable.tsx",
      "src/components/FilterFields.tsx",
      "src/components/SaveBar.tsx",
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
        "tests/i18n.test.mjs",
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
