// Página Inbox (Fase 8) — captura rápida de pensamentos soltos.
// A classificação (tipo/destino) é apenas uma sugestão da IA; nada é
// movido automaticamente.
import { api } from "../api.js";
import { esc } from "../helpers.js";

export function inboxView() {
  return {
    html: `
      <header class="page-header">
        <h1>Inbox</h1>
        <span class="badge">Fase 8</span>
      </header>

      <section class="settings-section">
        <p class="muted">Registre um pensamento solto (ideia, pergunta, descoberta…). Depois peça para classificar — a IA sugere o tipo e o destino, mas <strong>nada é movido sem a sua decisão</strong>.</p>
        <form class="entity-form" data-inbox-form>
          <label>Pensamento solto
            <textarea name="content" placeholder="Ex.: descobri que o novo Lambda só aceita arquivos menores que 6MB" required></textarea>
          </label>
          <div class="form-error" data-error></div>
          <button class="btn primary" type="submit">Salvar no Inbox</button>
        </form>
      </section>

      <section class="settings-section">
        <h2>Itens do Inbox</h2>
        <div class="recent-list" data-inbox-list></div>
      </section>
    `,
    async mount({ container }) {
      const inboxForm = container.querySelector("[data-inbox-form]");
      const inboxList = container.querySelector("[data-inbox-list]");

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
          err.textContent = "Erro ao salvar no Inbox. Tente novamente.";
          err.style.display = "block";
          return;
        }
        err.style.display = "none";
        inboxForm.reset();
        loadInbox();
      });

      await loadInbox();
    },
  };
}
