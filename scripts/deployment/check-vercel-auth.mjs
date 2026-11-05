import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";

// 応答本文・ユーザー情報・CLIの出力はログに記録しない。
export async function checkVercelAuth({
  token = process.env.VERCEL_TOKEN,
  request = fetch,
  run = spawnSync,
  report = console.log,
} = {}) {
  if (!token?.trim()) {
    report("VERCEL_TOKEN is not configured. Check the production environment Secret.");
    return false;
  }
  let response;
  try {
    response = await request("https://api.vercel.com/v2/user", {
      method: "GET",
      redirect: "error",
      signal: AbortSignal.timeout(15000),
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    report("Vercel user API request failed. Check network access and Vercel availability.");
    return false;
  }
  if (!response.ok) {
    report(`Vercel user API authentication failed: HTTP ${response.status}.`);
    report("Check token validity and issuing account; production Secrets override repository Secrets. Last active does not prove this request succeeded.");
    return false;
  }
  report("Vercel user API authentication passed.");
  try {
    const result = run("vercel", ["whoami", "--non-interactive"], {
      env: { ...process.env, VERCEL_TOKEN: token },
      stdio: "ignore",
      timeout: 30000,
    });
    if (result.error || result.status !== 0) {
      report("Vercel CLI authentication failed after user API authentication passed. Check the pinned CLI version and Vercel availability.");
      return false;
    }
  } catch {
    report("Vercel CLI authentication could not run.");
    return false;
  }
  report("Vercel CLI authentication passed.");
  return true;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  if (!(await checkVercelAuth())) process.exitCode = 1;
}
