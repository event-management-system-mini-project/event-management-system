const JSON_HEADERS = { accept: "application/json" };

export class ApiError extends Error {
  constructor(message, { status = 0, code = "request_failed", fields = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request(path, { method = "GET", body } = {}) {
  const options = {
    method,
    credentials: "same-origin",
    headers: { ...JSON_HEADERS },
  };
  if (body !== undefined) {
    options.headers["content-type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = csrfToken();
    if (token) options.headers["X-CSRFToken"] = token;
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new ApiError(
      "The server could not be reached. Check your connection and try again.",
      { code: "network_error" },
    );
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = data && data.error ? data.error : {};
    throw new ApiError(error.message || "The request could not be completed.", {
      status: response.status,
      code: error.code || "request_failed",
      fields: error.fields || null,
    });
  }
  return data;
}

export function getSession() {
  return request("/api/auth/session");
}

export function login(username, password) {
  return request("/api/auth/login", { method: "POST", body: { username, password } });
}

export function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export function listOwnEvents() {
  return request("/api/organizer/events");
}

export function createEvent(values) {
  return request("/api/events", { method: "POST", body: values });
}
