// 手動監査専用。固定のGET以外を行わず、資格情報・レスポンス全体を出力しない。
const projectId = "prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW";
const teamId = "team_tZDGBnNdyZxvlZvkV86h6SGv";
try {
  if (!process.env.VERCEL_TOKEN) throw new Error("VERCEL_TOKEN is not configured");
  const response = await fetch(`https://api.vercel.com/v9/projects/${projectId}?teamId=${teamId}`, {
    method: "GET",
    redirect: "error",
    signal: AbortSignal.timeout(15000),
    headers: { Authorization: `Bearer ${process.env.VERCEL_TOKEN}` },
  });
  if (!response.ok) throw new Error(`Vercel project GET failed: HTTP ${response.status}`);
  const p = await response.json();
  const matches = p.id === projectId && p.accountId === teamId && p.name === "grad-checker" && p.rootDirectory === "frontend" && p.nodeVersion === "24.x" && p.framework === "vite" && p.buildCommand === "npm run build" && p.installCommand === "npm ci";
  if (!matches) throw new Error("Vercel project configuration does not match the reviewed target");
  if (p.link != null || p.gitProviderOptions?.createDeployments !== "disabled" || p.gitProviderOptions?.disableRepositoryDispatchEvents !== true) throw new Error("Git automatic deployments must remain disconnected and disabled");
  console.log(JSON.stringify({ result: "passed", projectId, teamId, rootDirectory: p.rootDirectory, nodeVersion: p.nodeVersion, framework: p.framework, gitAutomaticDeployments: "disabled" }));
} catch (error) {
  // API/通信例外のmessageには資格情報が含まれる可能性があるため既知メッセージだけを表示。
  const message = error instanceof Error ? error.message : "";
  const known = /^(VERCEL_TOKEN is not configured|Vercel project GET failed: HTTP [0-9]{3}|Vercel project configuration does not match the reviewed target|Git automatic deployments must remain disconnected and disabled)$/;
  console.error(known.test(message) ? message : "Vercel read-only audit failed");
  process.exitCode = 1;
}
