import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const windows = process.platform === "win32";
const backendOnly = process.argv.includes("--backend-only");
const subjectListPreview =
  !backendOnly || process.argv.includes("--subject-list-preview");
const servers = [];
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
    "api_service.main:app",
    "--reload",
    "--host",
    "127.0.0.1",
    "--port",
    "8001",
  ],
  "backend/api/",
);
start(
  "Go API",
  "go",
  [
    "run",
    ".",
    ...(subjectListPreview ? ["-subject-list-preview"] : []),
  ],
  "backend/api/",
);
if (!backendOnly)
  start(
    "フロントエンド",
    "npm",
    ["run", "dev", "--", "--port", "5173", "--strictPort"],
    "frontend/",
  );
