import { mkdtemp, readdir, rm, writeFile, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const directory = await mkdtemp(join(tmpdir(), "grad-checker-tests-"));
async function testFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map((entry) => {
      const path = join(directory, entry.name);
      return entry.isDirectory()
        ? testFiles(path)
        : entry.isFile() && entry.name.endsWith(".test.mjs")
          ? [path]
          : [];
    }),
  );
  return files.flat().sort();
}
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
      "--project",
      "tsconfig.json",
      "--noEmit",
      "false",
      "--rootDir",
      "src",
      "--outDir",
      directory,
    ],
    { stdio: "inherit" },
  );
  if (compile.status !== 0) process.exitCode = compile.status ?? 1;
  else {
    const result = spawnSync(
      process.execPath,
      ["--test", ...(await testFiles("tests"))],
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
