// Página Inteligência (Fase 8) — Inbox + duplicatas + sugestões + gaps.
import { api } from "../api.js";
import { esc } from "../helpers.js";

export function intelligenceView() {
  return {
    html: `
      <header class="page-header">
        <h1>Inteligência</h1>
        <span class="badge">Fase 8</span>
      </header>

      <section class="settings-section">
        <h2>Inbox</h2>
        <form class="entity-form" data-inbox-form>
          <label>Pensamento solto
            <textarea name="content" placeholder="Registre uma ideia, pergunta, descoberta…" required></textarea>
          </label>
          <div class="form-error" data-error></div>
          <button class="btn primary" type="submit">Salvar no Inbox</button>
        </form>
        <div class="recent-list" data-inbox-list></div>
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
      const inboxForm = container.querySelector("[data-inbox-form]");
      const inboxList = container.querySelector("[data-inbox-list]");
      const dupEl = container.querySelector("[data-duplicates]");
      const relEl = container.querySelector("[data-rel]");
      const gapEl = container.querySelector("[data-gaps]");

      async function loadInbox() {
        const res = await api.get("/inbox/");
        const items = res.ok ? res.data.results || [] : [];
        if (!items.length) {
          inboxList.innerHTML = `<p class="muted">Inbox vazio. Registre algo acima.</p>`;
          return;
        }
        inboxList.innerHTML = items
          .map(
            (it) => `
              <div class="recent-item">
                <span class="search-body">
                  <span class="search-title">${esc(it.content)}</span>
                  <span class="search-snippet">classificação: ${esc(it.kind || "—")} → ${esc(it.destination || "—")} · ${esc(it.status)}</span>
                </span>
                <button class="btn ghost small" data-classify="${esc(it.id)}">Classificar</button>
              </div>`
          )
          .join("");
        inboxList.querySelectorAll("[data-classify]").forEach((btn) => {
          btn.addEventListener("click", async (e) => {
            e.target.disabled = true;
            await api.post(`/inbox/${btn.dataset.classify}/classify/`);
            loadInbox();
          });
        });
      }

      inboxForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const err = inboxForm.querySelector("[data-error]");
        const content = inboxForm.content.value.trim();
        if (!content) return;
        const res = await api.post("/inbox/", { content });
        if (!res.ok) {
          err.textContent = "Erro ao salvar no Inbox.";
          err.style.display = "block";
          return;
        }
        err.style.display = "none";
        inboxForm.reset();
        loadInbox();
      });

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

      await loadInbox();
      await loadAnalyses();
    },
  };
}
