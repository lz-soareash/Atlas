// Página do Atlas Assistant — chat RAG com conhecimento do Atlas (Fase 5).
// Consome POST /api/assistant/chat/ — fluxo: histórico → contexto → Gemini.
import { api } from "../api.js";
import { esc } from "../helpers.js";

// Rótulos amigáveis para cada tipo de entidade (espelha o backend).
const LABELS = {
  knowledge: "Conhecimento",
  idea: "Ideia",
  project: "Projeto",
  question: "Pergunta",
  decision: "Decisão",
  experience: "Experiência",
  relationship: "Relação",
};

function typeLabel(entity) {
  return LABELS[entity] || "Item";
}

export function assistantView() {
  let history = [];

  return {
    html: `
      <header class="page-header">
        <h1>Atlas Assistant</h1>
        <span class="badge">Fase 6</span>
      </header>
      <div class="chat-window">
        <div class="chat-log" data-chat-log>
          <p class="muted">Pergunte sobre seu conhecimento, projetos, ideias e memórias.</p>
        </div>
        <form class="chat-input" data-chat-form>
          <input type="text" name="message" placeholder="Pergunte ao Atlas…" autocomplete="off" />
          <button class="btn primary" type="submit">Enviar</button>
        </form>
        <div class="form-error" data-error></div>
      </div>
    `,
    mount({ container }) {
      const log = container.querySelector("[data-chat-log]");
      const form = container.querySelector("[data-chat-form]");
      const err = container.querySelector("[data-error]");
      const input = form.querySelector('input[name="message"]');

      function addMessage(role, content) {
        const first = log.querySelector(".muted");
        if (first) first.remove();
        const el = document.createElement("div");
        el.className = `chat-msg ${role}`;
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        bubble.textContent = content;
        el.appendChild(bubble);
        log.appendChild(el);
        log.scrollTop = log.scrollHeight;
        return el;
      }

      function renderSources(containerEl, sources) {
        if (!sources || !sources.length) return;
        const box = document.createElement("div");
        box.className = "chat-sources";
        box.innerHTML = `<div class="chat-sources-title">Fontes</div>`;
        sources.forEach((s, i) => {
          const a = document.createElement("a");
          a.className = "recent-item search-item";
          a.href = "#" + esc(s.route || "");
          a.innerHTML = `
            <span class="recent-tag"><span class="entity-dot" aria-hidden="true"></span>${esc(typeLabel(s.entity))}</span>
            <span class="search-body">
              <span class="search-title">${esc(s.title || "Sem título")}</span>
            </span>
            <span class="recent-score" title="score ${esc(s.score)}">${Number(s.score).toFixed(2)}</span>`;
          box.appendChild(a);
        });
        containerEl.appendChild(box);
      }

      function renderMeta(containerEl, data) {
        const meta = document.createElement("div");
        meta.className = "chat-meta";
        const tag = data.provider === "gemini" ? "gemini" : "local";
        meta.innerHTML = `<span class="muted">${esc(data.classification.label)} · AI: <strong>${esc(tag)}</strong></span>`;
        containerEl.insertBefore(meta, containerEl.firstChild);
      }

      function renderAgentSteps(containerEl, agentRun) {
        if (!agentRun || !agentRun.steps || !agentRun.steps.length) return;
        const box = document.createElement("div");
        box.className = "chat-agent-steps";
        box.innerHTML = `<div class="chat-sources-title">Passos executados (${agentRun.iterations} iteração(ões))</div>`;
        agentRun.steps.forEach((s, i) => {
          const row = document.createElement("div");
          row.className = "agent-step";
          const st = s.status === "ok" ? "✓" : "✕";
          row.innerHTML = `
            <span class="agent-step-iter">#${esc(s.iteration)}</span>
            <span class="agent-step-status" title="${esc(s.status)}">${st}</span>
            <span class="agent-step-body">
              <span class="agent-step-tool">${esc(s.tool)}</span>
              <span class="agent-step-summary">${esc(s.summary || "")}</span>
            </span>
          `;
          box.appendChild(row);
        });
        containerEl.appendChild(box);
      }

      function renderProposals(containerEl, proposals) {
        if (!proposals || !proposals.length) return;
        const box = document.createElement("div");
        box.className = "chat-proposals";
        proposals.forEach((p) => {
          const row = document.createElement("div");
          row.className = "proposal-row";
          const detail = (() => {
            const t = p.summary || p.entity;
            return esc(t);
          })();
          row.innerHTML = `
            <span class="proposal-detail">Proposta: ${detail}</span>
            <div class="proposal-actions">
              <button class="btn primary small" data-approve="${esc(p.id)}">Aprovar</button>
              <button class="btn ghost small" data-reject="${esc(p.id)}">Rejeitar</button>
            </div>
          `;
          box.appendChild(row);
        });
        containerEl.appendChild(box);

        box.querySelectorAll("[data-approve]").forEach((btn) => {
          btn.addEventListener("click", async (e) => {
            e.target.disabled = true;
            const id = btn.dataset.approve;
            const res = await api.post(`/tools/proposals/${id}/approve/`);
            btn.textContent = res.ok ? "Aprovado ✔" : "Falhou";
            btn.disabled = false;
            btn.closest(".proposal-row").querySelector("[data-reject]").disabled = res.ok;
          });
        });
        box.querySelectorAll("[data-reject]").forEach((btn) => {
          btn.addEventListener("click", async (e) => {
            e.target.disabled = true;
            const id = btn.dataset.reject;
            await api.post(`/tools/proposals/${id}/reject/`);
            btn.textContent = "Rejeitado";
            btn.closest(".proposal-row").querySelector("[data-approve]").disabled = true;
          });
        });
      }

      async function send(text) {
        err.style.display = "none";
        addMessage("user", text);
        history.push({ role: "user", content: text });

        const pending = addMessage("assistant", "…");
        pending.querySelector(".chat-bubble").classList.add("typing");

        try {
          const res = await api.post("/assistant/chat/", { messages: history });
          if (!res.ok) {
            const msg = res.data?.detail || "O Atlas não conseguiu responder agora.";
            if (res.status === 429) {
              throw new Error("Muitas solicitações em sequência. Aguarde alguns segundos e tente de novo.");
            }
            if (res.status === 502) {
              throw new Error("O assistente está indisponível no momento (IA offline). Tente de novo em instantes.");
            }
            throw new Error(msg);
          }
          pending.querySelector(".chat-bubble").classList.remove("typing");
          pending.querySelector(".chat-bubble").textContent = res.data.answer;
          renderMeta(pending, res.data);
          renderSources(pending, res.data.sources);
          renderAgentSteps(pending, res.data.agent_run);
          renderProposals(pending, res.data.proposals);
          history.push({ role: "assistant", content: res.data.answer });
          log.scrollTop = log.scrollHeight;
        } catch (ex) {
          pending.remove();
          err.textContent = ex.message;
          err.style.display = "block";
        }
      }

      form.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        send(text);
      });

      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) e.preventDefault();
      });
    },
  };
}
