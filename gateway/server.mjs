import http from "node:http";
import https from "node:https";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const envFile = fileURLToPath(new URL("../.env", import.meta.url));
if (existsSync(envFile)) process.loadEnvFile(envFile);

function error(response, status, code, message) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify({ error: { code, message } }));
}

function headersFor(headers) {
  const excluded = new Set([
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
    "x-organizer-id", "x-user-id", "x-forwarded-for", "x-forwarded-host",
    "x-forwarded-proto", "forwarded",
    ...(headers.connection || "").split(",").map((name) => name.trim().toLowerCase()),
  ]);
  return Object.fromEntries(Object.entries(headers).filter(([name]) => !excluded.has(name)));
}

export function createGateway(upstream = "http://127.0.0.1:8000", timeout = 5000, publicHost = null) {
  if (publicHost && !/^[a-zA-Z0-9.-]+(?::[0-9]+)?$/.test(publicHost)) {
    throw new Error("Use a hostname with an optional port for the HTTPS public host.");
  }
  const base = new URL(upstream);
  if (!["http:", "https:"].includes(base.protocol)) throw new Error("Use an HTTP(S) upstream.");
  const transport = base.protocol === "https:" ? https : http;
  return http.createServer((request, response) => {
    if (!request.url.startsWith("/api/")) {
      error(response, 404, "not_found", "The requested resource does not exist.");
      return;
    }
    // Fix the destination to the configured server; input cannot select another host.
    const target = new URL(base.origin + request.url);
    const headers = headersFor(request.headers);
    headers.host = base.host;
    if (publicHost) {
      headers.host = publicHost;
      headers["x-forwarded-proto"] = "https";
    }
    const proxy = transport.request(target, { method: request.method, headers }, (incoming) => {
      response.writeHead(incoming.statusCode, headersFor(incoming.headers));
      incoming.on("error", () => response.destroy());
      incoming.pipe(response);
    });
    proxy.setTimeout(timeout, () => proxy.destroy(new Error("upstream timeout")));
    proxy.on("error", () => {
      if (!response.headersSent) error(response, 502, "upstream_unavailable", "The API service is unavailable.");
      else response.destroy();
    });
    request.on("aborted", () => proxy.destroy());
    response.on("close", () => proxy.destroy());
    request.pipe(proxy);
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const server = createGateway(process.env.DJANGO_UPSTREAM, 5000, process.env.EMS_PUBLIC_HOST || null);
  const host = process.env.GATEWAY_HOST || "127.0.0.1";
  const port = Number(process.env.GATEWAY_PORT || 3000);
  server.listen(port, host, () => console.log(`API gateway: http://${host}:${server.address().port}`));
}
