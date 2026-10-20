import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const python = path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
if (!existsSync(python) || !existsSync(path.join(root, ".env"))) {
  console.error("Run python scripts/bootstrap.py first.");
  process.exit(1);
}
process.loadEnvFile(path.join(root, ".env"));
const upstream = new URL(process.env.DJANGO_UPSTREAM || "http://127.0.0.1:8000");
if (!["localhost", "127.0.0.1"].includes(upstream.hostname) || upstream.protocol !== "http:") {
  throw new Error("The development launcher requires a local HTTP Django upstream.");
}
const processes = [
  [python, ["backend/manage.py", "runserver", `127.0.0.1:${upstream.port || 80}`, "--noreload"]],
  [process.execPath, ["gateway/server.mjs"]],
  [process.execPath, ["node_modules/vite/bin/vite.js", "--config", "frontend/vite.config.mjs"]],
].map(([command, args]) => spawn(command, args, { cwd: root, stdio: "inherit", windowsHide: true }));

let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of processes) if (child.exitCode === null) child.kill();
  process.exitCode = code;
}
for (const child of processes) {
  child.on("error", (error) => { console.error(error.message); stop(1); });
  child.on("exit", (code) => { if (!stopping) stop(code ?? 1); });
}
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
console.log("Open http://127.0.0.1:5173. Press Ctrl+C to stop all three services.");
