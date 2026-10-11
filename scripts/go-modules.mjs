import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const [command, ...args] = process.argv.slice(2);
if (!["vet", "fmt", "test"].includes(command)) {
  console.error("指定できるGoコマンドはvet・fmt・testです。");
  process.exit(1);
}
// go.workに頼らず、各go.modとローカル依存指定で検証する。
for (const project of ["modules/subjects", "api", "tests"]) {
  const cwd = fileURLToPath(new URL(`../backend/${project}/`, import.meta.url));
  const result = spawnSync("go", [command, ...args, "./..."], {
    cwd,
    env: { ...process.env, GOWORK: "off" },
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.error) console.error(result.error.message);
  if (result.error || result.status !== 0) process.exit(result.status ?? 1);
}
