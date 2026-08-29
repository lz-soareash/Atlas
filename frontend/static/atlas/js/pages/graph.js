// Página Grafo — visualização de {nodes, edges} e criação de relacionamentos.
import { api } from "../api.js";
import { esc } from "../helpers.js";

const ENTITY_SOURCES = [
  { model: "knowledge.knowledge", api: "/knowledge/", label: "Conhecimento" },
  { model: "ideas.idea", api: "/ideas/", label: "Ideia" },
  { model: "projects.project", api: "/projects/", label: "Projeto" },
  { model: "questions.question", api: "/questions/", label: "Pergunta" },
  { model: "decisions.decision", api: "/decisions/", label: "Decisão" },
  { model: "experiences.experience", api: "/experiences/", label: "Experiência" },
];

const TYPES = [
  ["RELACIONADO_A", "Relacionado a"],
  ["USA", "Usa"],
  ["DEPENDE_DE", "Depende de"],
  ["ORIGINOU", "Originou"],
  ["INSPIROU", "Inspirou"],
  ["PARTICIPA_DE", "Participa de"],
  ["RESOLVE", "Resolve"],
  ["RESPONDE", "Responde"],
  ["AFETA", "Afeta"],
  ["GEROU", "Gerou"],
  ["APRENDEU_COM", "Aprendeu com"],
];

function optionsFor(instances) {
  const byModel = new Map(instances.map((g) => [g.model, g.items]));
  return ENTITY_SOURCES.flatMap((src) => {
    const items = byModel.get(src.model) || [];
    return items.map(
      (it) => `<option value="${src.model}|${it.id}">${src.label}: ${esc(it.name || it.title)}</option>`
    );
  }).join("");
}

export function graphView() {
  return {
    html: `
      <header class="page-header">
        <h1>Grafo</h1>
        <span class="badge">Fase 3</span>
      </header>

      <section class="settings-section">
        <h2>Novo relacionamento</h2>
        <form class="entity-form" data-rel-form>
          <label>Origem
            <select name="origin" data-origin><option value="">Carregando…</option></select>
          </label>
          <label>Tipo
            <select name="type">${TYPES.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("")}</select>
          </label>
          <label>Destino
            <select name="target" data-target><option value="">Carregando…</option></select>
          </label>
          <div class="form-error" data-error></div>
          <button class="btn primary" type="submit">Criar</button>
        </form>
      </section>

      <h2 class="section-title">Visualização</h2>
      <div data-graph-svg>
        <p class="muted">Carregando…</p>
      </div>
      <h3>Lista de arestas</h3>
      <div class="recent-list" data-edges>
        <p class="muted">Carregando…</p>
      </div>
    `,
    async mount({ container }) {
      const svgEl = container.querySelector("[data-graph-svg]");
      const edgesEl = container.querySelector("[data-edges]");
      const form = container.querySelector("[data-rel-form]");

      const [sources, graphRes] = await Promise.all([
        Promise.all(ENTITY_SOURCES.map(async (src) => {
          const res = await api.get(`${src.api}?page_size=100`);
          return { model: src.model, items: res.ok ? res.data.results || [] : [] };
        })),
        api.get("/graph/"),
      ]);

      const opts = optionsFor(sources);
      form.querySelector("[data-origin]").innerHTML = `<option value="">Selecione…</option>` + opts;
      form.querySelector("[data-target]").innerHTML = `<option value="">Selecione…</option>` + opts;

      function renderGraph() {
        const { nodes, edges } = graphRes.data;
        if (!nodes.length) {
          svgEl.innerHTML = `<p class="muted">Nenhum relacionamento ainda.</p>`;
          edgesEl.innerHTML = `<p class="muted">Nenhuma aresta.</p>`;
          return;
        }
        // Posicionamento circular dos nós em um SVG responsivo.
        const W = 720, H = 460, R = 190, cx = W / 2, cy = H / 2;
        const positions = {};
        nodes.forEach((n, i) => {
          const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
          positions[n.id] = { x: cx + R * Math.cos(angle), y: cy + R * Math.sin(angle) };
        });

        const edgesSvg = edges
          .map((e) => {
            const a = positions[e.source], b = positions[e.target];
            if (!a || !b) return "";
            return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"
              stroke="#7c5cff" stroke-width="1.5" opacity="0.7"/>`;
          })
          .join("");

        const nodesSvg = nodes
          .map((n) => {
            const p = positions[n.id];
            return `<g>
              <circle cx="${p.x}" cy="${p.y}" r="26" fill="#161b24" stroke="#2dd4bf" stroke-width="2"/>
              <text x="${p.x}" y="${p.y + 5}" text-anchor="middle" font-size="18" fill="#e6e9ef">${esc(n.emoji)}</text>
              <title>${esc(n.label)}: ${esc(n.title)}</title>
            </g>`;
          })
          .join("");

        const labels = nodes
          .map((n) => {
            const p = positions[n.id];
            return `<text x="${p.x}" y="${p.y + 42}" text-anchor="middle" font-size="11" fill="#8b93a3">${esc(n.title)}</text>`;
          })
          .join("");

        svgEl.innerHTML = `
          <svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:720px;background:var(--bg-elev);border:1px solid var(--border);border-radius:12px">
            ${edgesSvg}${nodesSvg}${labels}
          </svg>`;

        edgesEl.innerHTML = edges.length
          ? edges
              .map((e) => {
                const s = nodes.find((n) => n.id === e.source);
                const t = nodes.find((n) => n.id === e.target);
                return `<div class="recent-item">
                  <span class="recent-tag">${esc(e.label)}</span>
                  <span class="recent-title">${esc(s ? s.title : e.source)} → ${esc(t ? t.title : e.target)}</span>
                  <button class="btn ghost danger" data-del-edge="${e.id}">Excluir</button>
                </div>`;
              })
              .join("")
          : `<p class="muted">Nenhuma aresta.</p>`;
      }

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const err = container.querySelector("[data-error]");
        err.style.display = "none";
        const parse = (sel) => sel.value.split("|");
        const [om, oid] = parse(form.origin);
        const [tm, tid] = parse(form.target);
        if (!om || !tm || om === tm && oid === tid) {
          err.textContent = "Escolha origem e destino diferentes.";
          err.style.display = "block";
          return;
        }
        const res = await api.post("/relationships/", {
          type: form.type.value,
          origin: { model: om, id: oid },
          target: { model: tm, id: tid },
        });
        if (!res.ok) {
          const msg = res.data && (res.data.detail || Object.values(res.data).flat().join("; ")) || "Erro.";
          err.textContent = msg;
          err.style.display = "block";
          return;
        }
        await loadGraph();
        renderGraph();
      });

      async function loadGraph() {
        const res = await api.get("/graph/");
        if (res.ok) graphRes.data = res.data;
      }

      edgesEl.addEventListener("click", async (e) => {
        const del = e.target.closest("[data-del-edge]");
        if (!del) return;
        await api.delete(`/relationships/${del.dataset.delEdge}/`);
        await loadGraph();
        renderGraph();
      });

      renderGraph();
    },
  };
}
