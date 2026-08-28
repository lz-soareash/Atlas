// Páginas principais do aplicativo (Dashboard e módulos do Knowledge Core).
// Os módulos ainda serão implementados nas próximas fases; por ora exibem
// um cartão placeholder claro.
import { getUser } from "../auth.js";
import { esc } from "../helpers.js";

export function dashboardView() {
  const user = getUser();
  return {
    html: `
      <header class="page-header">
        <h1>Olá, ${esc(user?.first_name || user?.email || "")}</h1>
        <span class="badge">Fase 1</span>
      </header>
      <p class="muted">Seu Knowledge Operating System. Os módulos chegam nas próximas fases.</p>
    `,
  };
}

// Configuração dos módulos (título, descrição, fase e rota).
export const MODULES = [
  { key: "inbox", path: "/inbox", title: "Inbox", description: "Registre pensamentos soltos; a IA detecta tipo e relações.", phase: 8 },
  { key: "conhecimentos", path: "/conhecimentos", title: "Conhecimentos", description: "Conhecimentos adquiridos, com resumo, status e nível de domínio.", phase: 2 },
  { key: "ideias", path: "/ideias", title: "Ideias", description: "Ideias que podem evoluir para projetos.", phase: 2 },
  { key: "projetos", path: "/projetos", title: "Projetos", description: "Projetos com tecnologias, decisões e experiências.", phase: 2 },
  { key: "perguntas", path: "/perguntas", title: "Perguntas", description: "Perguntas ainda não respondidas, que podem gerar conhecimento.", phase: 2 },
  { key: "decisoes", path: "/decisoes", title: "Decisões", description: "Decisões com contexto, alternativas e justificativa.", phase: 2 },
  { key: "experiencias", path: "/experiencias", title: "Experiências", description: "Erros, soluções e aprendizados.", phase: 2 },
  { key: "grafo", path: "/grafo", title: "Grafo", description: "Visualização das conexões entre entidades.", phase: 3 },
  { key: "busca", path: "/busca", title: "Busca", description: "Busca híbrida (textual + semântica + grafo).", phase: 4 },
  { key: "assistente", path: "/assistente", title: "Assistente", description: "Atlas Assistant — chat com conhecimento do Atlas.", phase: 5 },
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
