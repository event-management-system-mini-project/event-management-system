import { afterEach, expect, it, vi } from "vitest";
import { registerForEvent } from "./api.js";

afterEach(() => vi.unstubAllGlobals());

it("sends the current CSRF token and session credentials when registering", async () => {
  document.cookie = "csrftoken=synthetic-token; path=/";
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: "saved" }) });
  vi.stubGlobal("fetch", fetch);
  await registerForEvent("event-one", { name: "Synthetic", email: "test@example.com" });
  expect(fetch).toHaveBeenCalledWith("/api/events/event-one/register", expect.objectContaining({
    method: "POST", credentials: "same-origin",
    headers: expect.objectContaining({ "X-CSRFToken": "synthetic-token" }),
  }));
});

it("preserves the registration endpoint's detail and field errors", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 400,
    json: async () => ({ detail: "Duplicate registration", fields: { email: ["Already registered"] } }),
  }));
  await expect(registerForEvent("event-one", {})).rejects.toMatchObject({
    message: "Duplicate registration", fields: { email: ["Already registered"] }, status: 400,
  });
});
