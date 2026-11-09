// Access to the Deno API on IBMI (proxied by Vite on /api). The session token lives in
// sessionStorage: it disappears when the tab is closed.

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

const STORAGE_KEY = "ibmi-jeton";
export const token = {
  get: () => sessionStorage.getItem(STORAGE_KEY),
  set: (t) => sessionStorage.setItem(STORAGE_KEY, t),
  clear: () => sessionStorage.removeItem(STORAGE_KEY),
};

let onExpired = () => {};
export const onSessionExpired = (f) => { onExpired = f; };

async function request(method, path, body) {
  const headers = { "content-type": "application/json" };
  const t = token.get();
  if (t) headers.authorization = `Bearer ${t}`;
  const r = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (r.status === 204) return null;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && path !== "/api/session") {
      token.clear();
      onExpired();
    }
    throw new ApiError(data.erreur ?? `HTTP error ${r.status}`, r.status, data);
  }
  return data;
}

// JSON field names (utilisateur, motDePasse, jeton, erreur…) are the API contract: unchanged
export const api = {
  signIn: (user, password) => request("POST", "/api/session", { utilisateur: user, motDePasse: password }),
  signOut: () => request("DELETE", "/api/session"),
  session: () => request("GET", "/api/session"),
  system: () => request("GET", "/api/systeme"),
  customers: (q = "") => request("GET", `/api/clients?q=${encodeURIComponent(q)}`),
  create: (record) => request("POST", "/api/clients", record),
  update: (id, record) => request("PUT", `/api/clients/${id}`, record),
  remove: (id) => request("DELETE", `/api/clients/${id}`),
};
