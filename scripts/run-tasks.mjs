import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const cwd = fileURLToPath(new URL("../", import.meta.url));
const probe = spawnSync("task", ["--version"], { cwd, stdio: "ignore" });
const runner = probe.error?.code === "ENOENT" ? "make" : "task";
const tasks = process.argv.slice(2);

for (const task of tasks.length ? tasks : ["check"]) {
  const result = spawnSync(runner, [task], { cwd, stdio: "inherit" });
  if (result.error) {
    console.error(`${runner} を実行できません: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}
