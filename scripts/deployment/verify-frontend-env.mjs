import { readdir, readFile } from "node:fs/promises";
import assert from "node:assert/strict";
const link = JSON.parse(await readFile(".vercel/project.json", "utf8"));
assert.equal(
  link.projectId,
  process.env.VERCEL_PROJECT_ID,
  "Unexpected Vercel project",
);
assert.equal(link.orgId, process.env.VERCEL_ORG_ID, "Unexpected Vercel team");
assert.equal(
  link.settings?.rootDirectory,
  "frontend",
  "Unexpected Vercel root directory",
);
assert.equal(link.settings?.framework, "vite", "Unexpected Vercel framework");
assert.equal(
  link.settings?.nodeVersion,
  "24.x",
  "Unexpected Vercel Node.js version",
);
for (const file of await readdir(".vercel")) {
  if (!file.startsWith(".env")) continue;
  const data = await readFile(`.vercel/${file}`, "utf8");
  for (const line of data.split("\n")) {
    const key = line.match(/^\s*([A-Z_][A-Z_0-9]*)=/)?.[1];
    if (key && /DATABASE|PGPASSWORD|SECRET|PRIVATE_KEY/.test(key)) {
      throw new Error(
        `Server credentials must not be configured in the frontend: ${key}`,
      );
    }
  }
}
