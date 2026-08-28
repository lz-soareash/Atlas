// Roteador por hash (ex.: #/conhecimentos) — SPA leve sem dependências.
import { isAuthenticated } from "./auth.js";

let routes = [];
let layout = null; // função que retorna a casca (sidebar + main)

export function setLayout(fn) {
  layout = fn;
}

export function setRoutes(list) {
  routes = list;
}

export function currentRoute() {
  const hash = window.location.hash.replace(/^#/, "") || "/";
  return hash.split("?")[0];
}

export function navigate(path) {
  window.location.hash = path;
}

function matchRoute(path) {
  for (const r of routes) {
    if (r.path === path) return { route: r, params: {} };
    const keys = [];
    const pattern = r.path.replace(/:[^/]+/g, (m) => {
      keys.push(m.slice(1));
      return "([^/]+)";
    });
    const re = new RegExp(`^${pattern}$`);
    const m = path.match(re);
    if (m) {
      const params = {};
      keys.forEach((k, i) => (params[k] = decodeURIComponent(m[i + 1])));
      return { route: r, params };
    }
  }
  return null;
}

export function render() {
  const path = currentRoute();
  let matched = matchRoute(path);

  if (matched && matched.route.auth && !isAuthenticated()) {
    navigate("/auth/login");
    return;
  }

  if (!matched) {
    matched = { route: routes.find((r) => r.path === "/_404") || { render: () => `<h1>404</h1>` } };
  }

  const { route, params } = matched;
  const container = document.getElementById("app");
  const page = route.view({ params });

  if (route.full === true) {
    container.innerHTML = page.html;
  } else if (layout) {
    container.innerHTML = layout({ inner: page.html, active: route.key || path });
  } else {
    container.innerHTML = page.html;
  }

  if (page.mount) page.mount({ params, container });
  if (route.afterMount) route.afterMount(page);
}
