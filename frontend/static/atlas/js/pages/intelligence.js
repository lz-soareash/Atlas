// Página Inteligência (Fase 8) — insights, produtividade e conselhos.
// Tudo aqui é SUGESTÃO baseada nos dados do usuário; nada é criado, movido
// ou deletado sem ação manual.
import { api } from "../api.js";
import { esc } from "../helpers.js";

function renderItems(items, emptyMsg) {
  if (!items || !items.length) {
    return `<p class="muted">${esc(emptyMsg)}</p>`;
  }
  return items
    .map(
      (it) => `
        <a class="recent-item" href="#${esc(it.route || "")}">
          <span class="search-body">
            <span class="search-title">${esc(it.title)}</span>
            <span class="search-snippet">${esc(it.detail || "")}</span>
          </span>
        </a>`
    )
    .join("");
}

export function intelligenceView() {
  return {
    html: `
      <header class="page-header">
        <h1>Inteligência</h1>
        <span class="badge">Fase 8</span>
        <p class="muted">Insights e conselhos baseados no seu acervo. <strong>Tudo é sugestão</strong> — nada acontece sem a sua ação.</p>
      </header>

      <section class="settings-section">
        <h2>Próximos passos sugeridos</h2>
        <div data-insights></div>
      </section>

      <section class="settings-section">
        <h2>Possíveis duplicatas</h2>
        <div class="recent-list" data-duplicates></div>
      </section>

      <section class="settings-section">
        <h2>Sugestões de relacionamentos</h2>
        <div class="recent-list" data-rel></div>
      </section>

      <section class="settings-section">
        <h2>Lacunas de conhecimento (Gaps)</h2>
        <div class="recent-list" data-gaps></div>
      </section>
    `,
    async mount({ container }) {
      const insightsEl = container.querySelector("[data-insights]");
      const dupEl = container.querySelector("[data-duplicates]");
      const relEl = container.querySelector("[data-rel]");
      const gapEl = container.querySelector("[data-gaps]");

      async function loadInsights() {
        const res = await api.get("/intelligence/insights/");
        const insights = res.ok ? res.data.insights || [] : [];
        if (!insights.length) {
          insightsEl.innerHTML = `<p class="muted">Nada pendente — acervo em dia. Sem sugestões de próximos passos.</p>`;
          return;
        }
        insightsEl.innerHTML = insights
          .map(
            (ins) => `
              <article class="insight-group">
                <h3>${esc(ins.title)}</h3>
                <p class="muted">${esc(ins.action)}</p>
                <div class="recent-list">${renderItems(ins.items, "—")}</div>
              </article>`
          )
          .join("");
      }

      async function loadAnalyses() {
        const [db, rel, gaps] = await Promise.all([
          api.get("/intelligence/duplicates/"),
          api.get("/intelligence/relationship-suggestions/"),
          api.get("/intelligence/gaps/"),
        ]);
        const groups = db.ok ? db.data.groups || [] : [];
        dupEl.innerHTML = groups.length
          ? groups
              .map(
                (g) => `
                  <a class="recent-item" href="#${esc(g.a.route)}">
                    <span class="search-body">
                      <span class="search-title">${esc(g.a.title)}</span>
                      <span class="search-snippet">≈ com: ${esc(g.b.title)} · sim ${g.similarity}</span>
                    </span>
                  </a>`
              )
              .join("")
          : `<p class="muted">Nenhuma duplicata provável.</p>`;

        const suggs = rel.ok ? rel.data.suggestions || [] : [];
        relEl.innerHTML = suggs.length
          ? suggs
              .map(
                (s) =>
                  `<a class="recent-item" href="#${esc(s.origin.route)}">
                    <span class="search-body">
                      <span class="search-title">${esc(s.origin.title)} ↔ ${esc(s.target.title)}</span>
                      <span class="search-snippet">sim ${s.similarity} · sugerido: ${esc(s.suggested)}</span>
                    </span>
                  </a>`
              )
              .join("")
          : `<p class="muted">Nenhuma sugestão de relacionamento.</p>`;

        const perGaps = gaps.ok ? gaps.data.gaps || [] : [];
        gapEl.innerHTML = perGaps.length
          ? perGaps
              .map(
                (g) =>
                  `<div class="recent-item">
                    <span class="search-body">
                      <span class="search-title">${esc(g.topic)}</span>
                      <span class="search-snippet">${g.mentions} menção(ões) sem conhecimento · ${esc(g.suggested)}</span>
                    </span>
                  </div>`
              )
              .join("")
          : `<p class="muted">Nenhuma lacuna detectada.</p>`;
      }

      await loadInsights();
      await loadAnalyses();
    },
  };
}
