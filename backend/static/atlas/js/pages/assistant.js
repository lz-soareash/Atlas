// Página do Atlas Assistant — chat com conhecimento do Atlas.
// A integração com o backend (POST /assistant/chat/) chega na Fase 5/6.
import { esc } from "../helpers.js";

export function assistantView() {
  return {
    html: `
      <header class="page-header">
        <h1>Atlas Assistant</h1>
        <span class="badge">Fase 5</span>
      </header>
      <div class="chat-window">
        <div class="chat-log" data-chat-log>
          <p class="muted">Pergunte sobre seu conhecimento, projetos e ideias.</p>
        </div>
        <form class="chat-input" data-chat-form>
          <input type="text" name="message" placeholder="Pergunte ao Atlas…" autocomplete="off" />
          <button class="btn primary" type="submit">Enviar</button>
        </form>
      </div>
    `,
    mount({ container }) {
      const log = container.querySelector("[data-chat-log]");
      const form = container.querySelector("[data-chat-form]");

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
      }

      form.addEventListener("submit", (e) => {
        e.preventDefault();
        const input = form.querySelector('input[name="message"]');
        const text = input.value.trim();
        if (!text) return;
        addMessage("user", text);
        input.value = "";
        // Integrar com POST /api/assistant/chat/ na Fase 5/6.
        addMessage("assistant", "O Atlas Assistant ainda está em construção (Fase 5).");
      });
    },
  };
}
