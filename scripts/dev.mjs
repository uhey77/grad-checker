import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const root = fileURLToPath(new URL("../", import.meta.url));
const windows = process.platform === "win32";
const backendOnly = process.argv.includes("--backend-only");
const subjectListPreview =
  !backendOnly || process.argv.includes("--subject-list-preview");
const servers = [];
const startupController = new AbortController();
let stopping = false;

function terminate(server, signal) {
  if (!server.child.pid) return;
  try {
    if (windows) {
      spawnSync("taskkill", ["/PID", String(server.child.pid), "/T", "/F"], {
        stdio: "ignore",
      });
    } else {
      // uvicornのリローダーやnpmの子プロセスも一緒に終了する。
      process.kill(-server.child.pid, signal);
    }
  } catch (error) {
    if (error.code !== "ESRCH") console.error(error.message);
  }
}

async function stop(code) {
  if (stopping) return;
  stopping = true;
  startupController.abort();
  for (const server of servers) terminate(server, "SIGTERM");
  let timer;
  await Promise.race([
    Promise.all(servers.map((server) => server.closed)),
    new Promise((resolve) => {
      timer = setTimeout(resolve, 3000);
    }),
  ]);
  clearTimeout(timer);
  for (const server of servers) terminate(server, "SIGKILL");
  process.exit(code);
}

function start(name, command, args, directory, environment = {}) {
  const child = spawn(command, args, {
    cwd: join(root, directory),
    env: { ...process.env, ...environment },
    stdio: "inherit",
    detached: !windows,
    shell: windows,
  });
  const server = {
    child,
    closed: new Promise((resolve) => child.once("close", resolve)),
  };
  servers.push(server);
  child.once("error", (error) => {
    console.error(`${name}を起動できませんでした: ${error.message}`);
    void stop(1);
  });
  child.once("exit", (code) => {
    if (!stopping) {
      console.error(`${name}が終了したため、開発サーバーを停止します。`);
      void stop(code || 1);
    }
  });
}

async function waitForBackend() {
  const url = "http://127.0.0.1:8000/api/auth/config";
  const timeout = AbortSignal.timeout(120_000);
  const signal = AbortSignal.any([startupController.signal, timeout]);
  console.log("バックエンドの起動完了を待っています…");
  while (!signal.aborted) {
    try {
      // GoからPythonへのブリッジ通信も成功するまで待つ。
      const response = await fetch(url, {
        signal: AbortSignal.any([signal, AbortSignal.timeout(1000)]),
        redirect: "error",
      });
      await response.body?.cancel();
      if (response.ok && !signal.aborted) return;
    } catch {
      // 接続拒否やリクエストのタイムアウトは起動中として再試行する。
    }
    try {
      await delay(250, undefined, { signal });
    } catch {
      break;
    }
  }
  if (!stopping)
    throw new Error(
      `バックエンドの起動が120秒以内に完了しませんでした: ${url}`,
    );
}

process.on("SIGINT", () => void stop(0));
process.on("SIGTERM", () => void stop(0));

console.log(
  `${backendOnly ? "バックエンド" : "フロントエンドとバックエンド"}を起動します。終了は Ctrl+C です。`,
);
start(
  "バックエンド",
  "uv",
  [
    "run",
    "--locked",
    "uvicorn",
    "apps.bridge.main:app",
    "--reload",
    "--host",
    "127.0.0.1",
    "--port",
    "8001",
  ],
  "backend/",
);
start(
  "Go API",
  "go",
  [
    "run",
    "./apps/api",
    "-public-origin",
    process.env.PUBLIC_ORIGIN || "http://127.0.0.1:5173",
    ...(subjectListPreview ? ["-subject-list-preview"] : []),
    ...(process.argv.includes("--api-docs") ? ["-api-docs"] : []),
  ],
  "backend/",
);
if (!backendOnly) {
  try {
    await waitForBackend();
    if (!stopping) {
      console.log("バックエンドの起動が完了しました。Viteを起動します。");
      start(
        "フロントエンド",
        "npm",
        ["run", "dev", "--", "--port", "5173", "--strictPort"],
        "frontend/",
      );
    }
  } catch (error) {
    console.error(error.message);
    await stop(1);
  }
}
