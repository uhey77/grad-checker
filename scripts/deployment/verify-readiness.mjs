import { readFileSync } from "node:fs";

try {
  const reply = JSON.parse(readFileSync(0, "utf8"));
  if (reply?.status !== "ok") throw new Error();
  console.log("Readiness JSON verified");
} catch {
  console.error("Readiness failed: expected a successful API JSON response");
  process.exitCode = 1;
}
