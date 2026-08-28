// Cliente HTTP da API Atlas com suporte a JWT + refresh automático.
export const API_BASE = "/api";

const TOKEN_KEY = "atlas_access";
const REFRESH_KEY = "atlas_refresh";

export const tokenStore = {
  get access() {
    return localStorage.getItem(TOKEN_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access, refresh) {
    localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  get hasSession() {
    return Boolean(this.access);
  },
};

async function rawRequest(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = tokenStore.access;
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  const text = await resp.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  return { status: resp.status, ok: resp.ok, data };
}

// Tenta renovar o access token com o refresh (uma única vez).
async function tryRefresh() {
  if (!tokenStore.refresh) return false;
  const resp = await fetch(`${API_BASE}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokenStore.refresh }),
  });
  if (!resp.ok) return false;
  const data = await resp.json();
  tokenStore.set(data.access);
  return true;
}

// Requisição com retry automático em caso de 401 (token expirado).
export async function request(method, path, body) {
  let res = await rawRequest(method, path, body);
  if (res.status === 401 && !path.includes("/auth/token/") && !path.includes("/accounts/register/")) {
    if (await tryRefresh()) {
      res = await rawRequest(method, path, body);
    }
  }
  return res;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  patch: (path, body) => request("PATCH", path, body),
  put: (path, body) => request("PUT", path, body),
  delete: (path) => request("DELETE", path),
};
