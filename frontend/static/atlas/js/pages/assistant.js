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
