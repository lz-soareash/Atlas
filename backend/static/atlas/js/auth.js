// Estado de autenticação do usuário.
import { api, tokenStore } from "./api.js";

let currentUser = null;

export function getUser() {
  return currentUser;
}

export async function loadCurrentUser() {
  if (!tokenStore.hasSession) {
    currentUser = null;
    return null;
  }
  const res = await api.get("/accounts/me/");
  currentUser = res.ok ? res.data : null;
  if (!res.ok) tokenStore.clear();
  return currentUser;
}

export async function login(email, password) {
  const res = await api.post("/auth/token/", { email, password });
  if (!res.ok) throw new Error(extractError(res));
  tokenStore.set(res.data.access, res.data.refresh);
  await loadCurrentUser();
}

export async function register(payload) {
  const res = await api.post("/accounts/register/", payload);
  if (!res.ok) throw new Error(extractError(res));
  tokenStore.set(res.data.access, res.data.refresh);
  currentUser = res.data.user;
  return currentUser;
}

export function logout() {
  tokenStore.clear();
  currentUser = null;
}

export function isAuthenticated() {
  return Boolean(currentUser || tokenStore.hasSession);
}

function extractError(res) {
  const d = res.data;
  if (!d) return "Erro de conexão com o servidor.";
  if (typeof d === "string") return d;
  if (d.detail) return d.detail;
  if (d.email) return (Array.isArray(d.email) ? d.email : [d.email])[0];
  if (d.password_confirmation) {
    return (Array.isArray(d.password_confirmation) ? d.password_confirmation : [d.password_confirmation])[0];
  }
  return "Não foi possível concluir a operação.";
}
