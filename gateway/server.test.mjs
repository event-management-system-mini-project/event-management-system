import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { once } from "node:events";
import { createGateway } from "./server.mjs";

async function listen(server) {
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  return `http://127.0.0.1:${server.address().port}`;
}
function cleanup(t, server) {
  t.after(() => new Promise((resolve) => {
    server.close(resolve);
    server.closeAllConnections();
  }));
}

test("forwards API body, cookies, CSRF and status without accepting identity headers", async (t) => {
  let observed;
  const api = http.createServer(async (req, res) => {
    let body = "";
    for await (const chunk of req) body += chunk;
    observed = { path: req.url, method: req.method, body, headers: req.headers };
    res.writeHead(201, {
      "content-type": "application/json",
      "set-cookie": ["sessionid=synthetic; HttpOnly; SameSite=Lax"],
    });
    res.end(JSON.stringify({ registration: { id: "example" } }));
  });
  cleanup(t, api);
  const gateway = createGateway(await listen(api));
  cleanup(t, gateway);
  const base = await listen(gateway);
  const response = await fetch(base + "/api/events/123/registrations?example=1", {
    method: "POST",
    headers: {
      "content-type": "application/json", cookie: "sessionid=synthetic",
      "x-csrftoken": "synthetic-csrf", "x-organizer-id": "spoofed",
      "x-forwarded-proto": "https",
    },
    body: JSON.stringify({ name: "Synthetic Attendee", email: "student@example.com" }),
  });
  assert.equal(response.status, 201);
  assert.equal(observed.path, "/api/events/123/registrations?example=1");
  assert.equal(observed.method, "POST");
  assert.equal(JSON.parse(observed.body).name, "Synthetic Attendee");
  assert.equal(observed.headers.cookie, "sessionid=synthetic");
  assert.equal(observed.headers["x-csrftoken"], "synthetic-csrf");
  assert.equal(observed.headers["x-organizer-id"], undefined);
  assert.equal(observed.headers["x-forwarded-proto"], undefined);
  assert.match(response.headers.get("set-cookie"), /HttpOnly/);
});

test("returns safe JSON when Django is unavailable", async (t) => {
  const closed = http.createServer();
  const address = await listen(closed);
  await new Promise((resolve) => closed.close(resolve));
  const gateway = createGateway(address);
  cleanup(t, gateway);
  const response = await fetch((await listen(gateway)) + "/api/health");
  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), {
    error: { code: "upstream_unavailable", message: "The API service is unavailable." },
  });
});

test("does not proxy non-API routes", async (t) => {
  const gateway = createGateway();
  cleanup(t, gateway);
  const response = await fetch((await listen(gateway)) + "/other");
  assert.equal(response.status, 404);
  assert.equal((await response.json()).error.code, "not_found");
});
