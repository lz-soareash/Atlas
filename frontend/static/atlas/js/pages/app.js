// Páginas principais do aplicativo (Dashboard).
// O Dashboard consome GET /api/dashboard/ para mostrar contagens e recentes.
import { getUser } from "../auth.js";
import { api } from "../api.js";
import { esc } from "../helpers.js";
import { navigate } from "../router.js";

export function dashboardView() {
  const user = getUser();
  return {
    html: `
      <header class="page-header">
        <h1>Olá, ${esc(user?.first_name || user?.email || "")}</h1>
        <span class="badge">Dashboard</span>
      </header>
      <div class="stat-grid" data-counts>
        <p class="muted">Carregando…</p>
      </div>
      <h2 class="section-title">Atividade recente</h2>
      <div class="recent-list" data-recent>
        <p class="muted">Carregando…</p>
      </div>
    `,
    async mount({ container }) {
      const countsEl = container.querySelector("[data-counts]");
      const recentEl = container.querySelector("[data-recent]");
      const res = await api.get("/dashboard/");
      if (!res.ok) {
        countsEl.innerHTML = `<p class="muted">Não foi possível carregar o dashboard.</p>`;
        return;
      }
      const { counts, recent } = res.data;

      countsEl.innerHTML = counts
        .map(
          (c) => `
            <a class="stat-card" href="#${c.route}" onclick="location.hash='#${c.route}'">
              <div class="stat-value">${c.count}</div>
              <div class="stat-label">${esc(c.label)}</div>
            </a>
          `
        )
        .join("");

      recentEl.innerHTML = recent.length
        ? recent
            .map(
              (r) => `
                <a class="recent-item" data-route="${r.route}">
                  <span class="recent-tag">${esc(r.label)}</span>
                  <span class="recent-title">${esc(r.title)}</span>
                  <span class="recent-status">${esc(r.status || "")}</span>
                </a>
              `
            )
            .join("")
        : `<p class="muted">Nenhuma atividade ainda. Comece criando um conhecimento, uma ideia, um projeto…</p>`;

      recentEl.querySelectorAll("[data-route]").forEach((el) => {
        el.addEventListener("click", () => navigate(el.dataset.route));
      });
    },
  };
}

// Configuração dos módulos (título, descrição, fase e rota).
export const MODULES = [
  { key: "inbox", path: "/inbox", title: "Inbox", description: "Registre pensamentos soltos; a IA detecta tipo e relações.", phase: 8 },
  { key: "inteligencia", path: "/inteligencia", title: "Inteligência", description: "Duplicatas, sugestões de vínculos e lacunas de conhecimento.", phase: 8 },
  { key: "conhecimentos", path: "/conhecimentos", title: "Conhecimentos", description: "Conhecimentos adquiridos, com resumo, status e nível de domínio.", phase: 2 },
  { key: "ideias", path: "/ideias", title: "Ideias", description: "Ideias que podem evoluir para projetos.", phase: 2 },
  { key: "projetos", path: "/projetos", title: "Projetos", description: "Projetos com tecnologias, decisões e experiências.", phase: 2 },
  { key: "perguntas", path: "/perguntas", title: "Perguntas", description: "Perguntas ainda não respondidas, que podem gerar conhecimento.", phase: 2 },
  { key: "decisoes", path: "/decisoes", title: "Decisões", description: "Decisões com contexto, alternativas e justificativa.", phase: 2 },
  { key: "experiencias", path: "/experiencias", title: "Experiências", description: "Erros, soluções e aprendizados.", phase: 2 },
  { key: "grafo", path: "/grafo", title: "Grafo", description: "Visualização das conexões entre entidades.", phase: 3 },
  { key: "busca", path: "/busca", title: "Busca", description: "Busca híbrida (textual + semântica + grafo).", phase: 4 },
  { key: "assistente", path: "/assistente", title: "Assistente", description: "Atlas Assistant — chat com conhecimento do Atlas.", phase: 6 },
  { key: "memoria", path: "/memoria", title: "Memória", description: "Preferências, contexto e objetivos do usuário.", phase: 6 },
  { key: "configuracoes", path: "/configuracoes", title: "Configurações", description: "Preferências do usuário e do Assistant.", phase: 1 },
];

export function placeholderView(module) {
  return {
    html: `
      <header class="page-header">
        <h1>${esc(module.title)}</h1>
        <span class="badge">Fase ${module.phase}</span>
      </header>
      <p class="muted">${esc(module.description)}</p>
      <div class="placeholder">Em construção — será implementado na Fase ${module.phase}.</div>
    `,
  };
}

export function notFoundView() {
  return {
    html: `
      <header class="page-header"><h1>404</h1></header>
      <p class="muted">Página não encontrada.</p>
      <a href="#/" class="btn primary">Ir para o início</a>
    `,
  };
}
