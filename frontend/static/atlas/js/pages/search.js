// Página Busca — busca híbrida (textual + semântica) em todas as entidades.
import { api } from "../api.js";
import { esc } from "../helpers.js";

const TYPES = [
  ["", "Todos"],
  ["knowledge", "Conhecimento"],
  ["idea", "Ideia"],
  ["project", "Projeto"],
  ["question", "Pergunta"],
  ["decision", "Decisão"],
  ["experience", "Experiência"],
];

export function searchView() {
  return {
    html: `
      <header class="page-header">
        <h1>Busca</h1>
        <span class="badge">Fase 4</span>
      </header>

      <section class="settings-section">
        <form class="entity-form" data-search-form>
          <label>Buscar
            <input type="search" name="q" data-query placeholder="Buscar em conhecimentos, ideias, projetos…" />
          </label>
          <label>Tipo
            <select name="type">${TYPES.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("")}</select>
          </label>
          <div class="form-error" data-error></div>
          <button class="btn primary" type="submit">Buscar</button>
        </form>
      </section>

      <div class="search-meta" data-meta></div>
      <div class="recent-list" data-results>
        <p class="muted">Digite um termo para buscar em todo o Atlas.</p>
      </div>
    `,
    async mount({ container }) {
      const form = container.querySelector("[data-search-form]");
      const resultsEl = container.querySelector("[data-results]");
      const metaEl = container.querySelector("[data-meta]");
      const err = container.querySelector("[data-error]");

      async function run(query, type) {
        if (!query) {
          resultsEl.innerHTML = `<p class="muted">Digite um termo para buscar em todo o Atlas.</p>`;
          metaEl.innerHTML = "";
          return;
        }
        const params = new URLSearchParams({ q: query });
        if (type) params.set("type", type);
        const res = await api.get(`/search/?${params}`);
        if (!res.ok) {
          const msg = res.data && (res.data.detail || Object.values(res.data).flat().join("; ")) || "Erro na busca.";
          throw new Error(msg);
        }
        const { results, semantic_available } = res.data;
        const tag = semantic_available ? "semântica" : "textual";
        metaEl.innerHTML =
          results.length
            ? `<span class="muted">${results.length} resultado(s) · busca ${esc(tag)}</span>`
            : `<span class="muted">Nenhum resultado para “${esc(query)}”.</span>`;
        resultsEl.innerHTML =
          results.length
            ? results
                .map(
                  (r) => `
                  <a class="recent-item search-item" href="#${r.route}">
                    <span class="recent-tag"><span class="entity-dot" aria-hidden="true"></span>${esc(r.label)}</span>
                    <span class="search-body">
                      <span class="search-title">${esc(r.title)}</span>
                      <span class="search-snippet">${esc(r.snippet)}</span>
                    </span>
                    <span class="recent-score" title="score ${esc(r.score)}">${Number(r.score).toFixed(2)}</span>
                  </a>`
                )
                .join("")
            : `<p class="muted">Nenhum resultado para “${esc(query)}”.</p>`;
      }

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        err.style.display = "none";
        try {
          await run(form.q.value.trim(), form.type.value);
        } catch (ex) {
          err.textContent = ex.message;
          err.style.display = "block";
        }
      });
    },
  };
}
