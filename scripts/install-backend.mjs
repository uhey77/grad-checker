import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

// 各プロジェクトのロックと仮想環境を個別に同期する。
for (const project of ["modules/subjects", "config", "api", "."]) {
  const cwd = fileURLToPath(new URL(`../backend/${project}/`, import.meta.url));
  const result = spawnSync("uv", ["sync", "--locked"], {
    cwd,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.error) console.error(result.error.message);
  if (result.error || result.status !== 0) process.exit(result.status ?? 1);
}
