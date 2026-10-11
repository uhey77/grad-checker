import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const cwd = fileURLToPath(new URL("../backend/", import.meta.url));
const result = spawnSync("gofmt", ["-l", "api", "modules", "tests"], {
  cwd,
  encoding: "utf8",
});
if (result.error) {
  console.error(`gofmtを実行できません: ${result.error.message}`);
  process.exit(1);
}
if (result.status !== 0) {
  console.error(result.stderr);
  process.exit(result.status ?? 1);
}
if (result.stdout.trim()) {
  console.error(`Goの整形が必要です:\n${result.stdout}`);
  process.exit(1);
}
