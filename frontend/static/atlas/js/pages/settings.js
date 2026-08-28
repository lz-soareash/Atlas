// Página de Configurações — perfil, dados da conta e preferências do Assistant.
import { getUser, loadCurrentUser } from "../auth.js";
import { api } from "../api.js";
import { esc } from "../helpers.js";

const PREFS_KEY = "atlas_assistant_prefs";

function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
  } catch {
    return {};
  }
}

function savePrefs(prefs) {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
}

export function settingsView() {
  const user = getUser();

  return {
    html: `
      <header class="page-header">
        <h1>Configurações</h1>
        <span class="badge">Fase 1</span>
      </header>

      <section class="settings-section">
        <h2>Perfil</h2>
        <form class="entity-form" data-profile-form>
          <label>Nome
            <input type="text" name="first_name" value="${esc(user?.first_name || "")}" />
          </label>
          <label>Sobrenome
            <input type="text" name="last_name" value="${esc(user?.last_name || "")}" />
          </label>
          <div class="form-error" data-error></div>
          <div class="form-success" data-success></div>
          <button class="btn primary" type="submit">Salvar perfil</button>
        </form>
      </section>

      <section class="settings-section">
        <h2>Conta</h2>
        <dl class="account-info">
          <div><dt>E-mail</dt><dd>${esc(user?.email || "")}</dd></div>
          <div><dt>Membro desde</dt><dd>${user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}</dd></div>
          <div><dt>ID</dt><dd class="mono">${esc(user?.id || "")}</dd></div>
        </dl>
      </section>

      <section class="settings-section">
        <h2>Preferências do Assistant</h2>
        <form class="entity-form" data-prefs-form>
          <label>Tema da resposta
            <select name="tone">
              <option value="claro">Claro e direto</option>
              <option value="amigavel">Amigável e encorajador</option>
              <option value="tecnico">Técnico e detalhado</option>
            </select>
          </label>
          <label>Sugerir próximos passos
            <select name="suggestions">
              <option value="yes">Sim</option>
              <option value="no">Não</option>
            </select>
          </label>
          <div class="form-success" data-success></div>
          <button class="btn primary" type="submit">Salvar preferências</button>
        </form>
        <p class="muted note">As preferências são salvas localmente neste navegador por enquanto.</p>
      </section>
    `,
    mount({ container }) {
      const profileForm = container.querySelector("[data-profile-form]");
      const prefsForm = container.querySelector("[data-prefs-form]");

      function showSuccess(form) {
        const box = form.querySelector("[data-success]");
        box.textContent = "Salvo.";
        box.style.display = "block";
        setTimeout(() => (box.style.display = "none"), 2200);
      }

      profileForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const err = profileForm.querySelector("[data-error]");
        err.style.display = "none";
        const body = {
          first_name: profileForm.first_name.value,
          last_name: profileForm.last_name.value,
        };
        const res = await api.patch("/accounts/me/", body);
        if (!res.ok) {
          const msg = res.data && Object.values(res.data).flat().join("; ") || "Erro ao salvar perfil.";
          err.textContent = msg;
          err.style.display = "block";
          return;
        }
        await loadCurrentUser();
        showSuccess(profileForm);
      });

      const prefs = loadPrefs();
      if (prefs.tone) prefsForm.tone.value = prefs.tone;
      if (prefs.suggestions) prefsForm.suggestions.value = prefs.suggestions;

      prefsForm.addEventListener("submit", (e) => {
        e.preventDefault();
        savePrefs({ tone: prefsForm.tone.value, suggestions: prefsForm.suggestions.value });
        showSuccess(prefsForm);
      });
    },
  };
}
