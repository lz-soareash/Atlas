// Páginas genéricas das entidades do Knowledge Core (Fase 2).
// Cada entidade possui uma configuração de campos e um endpoint da API.
import { api } from "../api.js";
import { esc } from "../helpers.js";

export const ENTITY_CONFIGS = {
  conhecimentos: {
    api: "/knowledge/",
    sing: "Conhecimento",
    fields: [
      { name: "title", label: "Título", type: "text", required: true },
      { name: "summary", label: "Resumo", type: "textarea" },
      { name: "content", label: "Conteúdo", type: "textarea" },
      {
        name: "domain_level",
        label: "Nível de domínio",
        type: "select",
        options: [
          ["1", "Iniciante"],
          ["2", "Intermediário"],
          ["3", "Avançado"],
          ["4", "Especialista"],
        ],
      },
    ],
    columns: (r) => [
      esc(r.title),
      esc(r.status),
      esc(r.domain_level_label),
      new Date(r.created_at).toLocaleDateString(),
    ],
  },
  ideias: {
    api: "/ideas/",
    sing: "Ideia",
    fields: [
      { name: "title", label: "Título", type: "text", required: true },
      { name: "description", label: "Descrição", type: "textarea" },
      { name: "summary", label: "Resumo", type: "textarea" },
    ],
    columns: (r) => [esc(r.title), esc(r.status), esc(r.converted ? "Convertida" : ""), new Date(r.created_at).toLocaleDateString()],
    transform: { label: "Converter em Projeto", endpoint: "convert", method: "post", prompt: "Nome do projeto (opcional)?" },
  },
  projetos: {
    api: "/projects/",
    sing: "Projeto",
    fields: [
      { name: "name", label: "Nome", type: "text", required: true },
      { name: "objective", label: "Objetivo", type: "textarea" },
      { name: "description", label: "Descrição", type: "textarea" },
      { name: "technologies", label: "Tecnologias (separadas por vírgula)", type: "tags" },
    ],
    columns: (r) => [esc(r.name), esc(r.status), (r.technologies || []).join(", "), new Date(r.created_at).toLocaleDateString()],
  },
  perguntas: {
    api: "/questions/",
    sing: "Pergunta",
    fields: [
      { name: "title", label: "Pergunta", type: "text", required: true },
      { name: "question_text", label: "Detalhes", type: "textarea" },
      { name: "summary", label: "Resumo", type: "textarea" },
    ],
    columns: (r) => [esc(r.title), esc(r.status), esc(r.answered ? "Respondida" : ""), new Date(r.created_at).toLocaleDateString()],
    transform: { label: "Responder (vira Conhecimento)", endpoint: "respond", method: "post", prompt: "Resposta/conteúdo?" },
  },
  decisoes: {
    api: "/decisions/",
    sing: "Decisão",
    fields: [
      { name: "title", label: "Título", type: "text", required: true },
      { name: "context", label: "Contexto", type: "textarea" },
      { name: "problem", label: "Problema", type: "textarea" },
      { name: "decision", label: "Decisão", type: "textarea" },
      { name: "rationale", label: "Justificativa", type: "textarea" },
      { name: "alternatives", label: "Alternativas (cada uma em linha)", type: "list" },
    ],
    columns: (r) => [esc(r.title), esc(r.status), esc(r.decision), new Date(r.created_at).toLocaleDateString()],
  },
  experiencias: {
    api: "/experiences/",
    sing: "Experiência",
    fields: [
      { name: "title", label: "Título", type: "text", required: true },
      {
        name: "kind",
        label: "Tipo",
        type: "select",
        options: [
          ["error", "Erro"],
          ["solution", "Solução"],
          ["discovery", "Descoberta"],
          ["experiment", "Experimento"],
          ["lesson", "Aprendizado"],
        ],
      },
      { name: "content", label: "Conteúdo", type: "textarea" },
      { name: "tags", label: "Tags (separadas por vírgula)", type: "tags" },
    ],
    columns: (r) => [esc(r.title), esc(r.kind_label), esc(r.status), new Date(r.created_at).toLocaleDateString()],
  },
};

// Transforma payload de formulário (tags/lists) no formato da API.
function normalizePayload(config, form) {
  const data = {};
  for (const f of config.fields) {
    const el = form.elements[f.name];
    if (!el) continue;
    let val = el.value;
    if (f.type === "tags") {
      val = val.split(",").map((s) => s.trim()).filter(Boolean);
    } else if (f.type === "list") {
      val = val.split("\n").map((s) => s.trim()).filter(Boolean);
    }
    data[f.name] = val;
  }
  return data;
}

function formHtml(fields) {
  return fields
    .map((f) => {
      const req = f.required ? "required" : "";
      if (f.type === "textarea") {
        return `<label>${esc(f.label)}<textarea name="${f.name}" ${req}></textarea></label>`;
      }
      if (f.type === "select") {
        const opts = f.options.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("");
        return `<label>${esc(f.label)}<select name="${f.name}">${opts}</select></label>`;
      }
      return `<label>${esc(f.label)}<input type="text" name="${f.name}" ${req} /></label>`;
    })
    .join("");
}

export function entityView(module) {
  const config = ENTITY_CONFIGS[module.key];
  return {
    html: `
      <header class="page-header">
        <h1>${esc(module.title)}</h1>
        <span class="badge">Fase 2</span>
      </header>
      <form class="entity-form" data-entity-form>
        <h2>Novo ${esc(config.sing)}</h2>
        ${formHtml(config.fields)}
        <div class="form-error" data-error></div>
        <button class="btn primary" type="submit">Salvar</button>
      </form>
      <h2>Lista</h2>
      <div class="entity-list" data-entity-list>
        <p class="muted">Carregando…</p>
      </div>
    `,
    async mount({ container }) {
      const form = container.querySelector("[data-entity-form]");
      const listEl = container.querySelector("[data-entity-list]");
      const perConfig = config.transform;

      async function load() {
        const res = await api.get(config.api);
        if (!res.ok) {
          listEl.innerHTML = `<p class="muted">Não foi possível carregar.</p>`;
          return;
        }
        const items = res.data.results || [];
        if (!items.length) {
          listEl.innerHTML = `<p class="muted">Nenhum registro ainda.</p>`;
          return;
        }
        const headers = ["Título", "Status", ...(perConfig ? [""] : [])].map(
          (h) => `<th>${h}</th>`
        ).join("") + `<th></th>`;
        listEl.innerHTML = `
          <table class="entity-table">
            <thead><tr>${headers}</tr></thead>
            <tbody>
              ${items
                .map(
                  (r) => `
                    <tr>
                      ${config.columns(r).map((c) => `<td>${c}</td>`).join("")}
                      <td class="actions">
                        ${perConfig ? `<button class="btn ghost" data-act="${r.id}">${esc(perConfig.label)}</button>` : ""}
                        <button class="btn ghost danger" data-del="${r.id}">Excluir</button>
                      </td>
                    </tr>
                  `
                )
                .join("")}
            </tbody>
          </table>
        `;
      }

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const res = await api.post(config.api, normalizePayload(config, form));
        const err = container.querySelector("[data-error]");
        if (!res.ok) {
          const msg = res.data && (res.data.detail || Object.values(res.data).flat().join("; ")) || "Erro ao salvar.";
          err.textContent = msg;
          err.style.display = "block";
          return;
        }
        err.style.display = "none";
        form.reset();
        load();
      });

      listEl.addEventListener("click", async (e) => {
        const del = e.target.closest("[data-del]");
        const act = e.target.closest("[data-act]");
        if (del) {
          await api.delete(config.api + del.dataset.del + "/");
          load();
        } else if (act) {
          const id = act.dataset.act;
          const userText = perConfig.prompt ? window.prompt(perConfig.prompt) : "";
          const body = { content: userText || "" };
          if (module.key === "ideias") body.name = userText;
          await api.post(config.api + id + "/" + perConfig.endpoint + "/", body);
          load();
        }
      });

      load();
    },
  };
}
