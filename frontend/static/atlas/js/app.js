// Bootstrap do frontend Atlas (SPA em HTML/CSS/JS puro).
// Carregado como <script type="module"> — organizado em módulos ES.

import { getUser, isAuthenticated, loadCurrentUser, logout } from "./auth.js";
import { esc } from "./helpers.js";
import { setLayout, setRoutes, navigate, currentRoute, render } from "./router.js";

import { loginView, registerView } from "./pages/auth.js";
import { dashboardView, MODULES, placeholderView, notFoundView } from "./pages/app.js";
import { entityView, ENTITY_CONFIGS } from "./pages/entities.js";
import { graphView } from "./pages/graph.js";
import { searchView } from "./pages/search.js";
import { assistantView } from "./pages/assistant.js";
import { settingsView } from "./pages/settings.js";

// Itens da barra lateral.
const NAV_ITEMS = [
  { path: "/", label: "Dashboard", key: "" },
  ...MODULES.map((m) => ({ path: m.path, label: m.title, key: m.key })),
];

// Layout compartilhado: sidebar + conteúdo.
function layout({ inner, active }) {
  const user = getUser();
  const firstName = user?.first_name || user?.email || "";
  return `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="sidebar-brand">Atlas</div>
        <nav class="sidebar-nav">
          ${NAV_ITEMS.map(
            (n) => `
              <a href="#${n.path === "/" ? "/" : n.path}"
                 class="nav-link ${active === n.key ? "active" : ""}">${esc(n.label)}</a>
            `
          ).join("")}
        </nav>
        <div class="sidebar-footer">
          <span class="user-email" title="${esc(user?.email || "")}">${esc(firstName)}</span>
          <button class="btn ghost" type="button" data-logout>Sair</button>
        </div>
      </aside>
      <main class="main">${inner}</main>
    </div>
  `;
}

// Registro das rotas.
function defineRoutes() {
  const appRoutes = [
    { path: "/", key: "", auth: true, view: dashboardView },
    ...MODULES.map((m) => {
      if (m.key === "assistente") {
        return { path: m.path, key: m.key, auth: true, view: assistantView };
      }
      if (m.key === "configuracoes") {
        return { path: m.path, key: m.key, auth: true, view: settingsView };
      }
      if (m.key === "grafo") {
        return { path: m.path, key: m.key, auth: true, view: graphView };
      }
      if (m.key === "busca") {
        return { path: m.path, key: m.key, auth: true, view: searchView };
      }
      if (ENTITY_CONFIGS[m.key]) {
        return { path: m.path, key: m.key, auth: true, view: () => entityView(m) };
      }
      return { path: m.path, key: m.key, auth: true, view: () => placeholderView(m) };
    }),
    { path: "/_404", view: notFoundView },
  ];
  const authRoutes = [
    { path: "/auth/login", full: true, view: loginView },
    { path: "/auth/register", full: true, view: registerView },
  ];
  setRoutes([...authRoutes, ...appRoutes]);
}

function handleLogout() {
  const btn = document.querySelector("[data-logout]");
  if (btn) {
    btn.addEventListener("click", () => {
      logout();
      navigate("/auth/login");
    });
  }
}

// Guarda global: se autenticado e na rota de auth, vai para o início.
function redirectIfNeeded() {
  const path = currentRoute();
  if (isAuthenticated() && (path === "/auth/login" || path === "/auth/register")) {
    navigate("/");
  }
}

async function boot() {
  setLayout(layout);
  defineRoutes();
  await loadCurrentUser();
  redirectIfNeeded();

  window.addEventListener("hashchange", () => {
    redirectIfNeeded();
    render();
    handleLogout();
  });

  render();
  handleLogout();
}

boot();
