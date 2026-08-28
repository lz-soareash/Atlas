// Páginas de autenticação (login e registro) — HTML/CSS/JS puro.
import { login, register } from "../auth.js";
import { esc, setError } from "../helpers.js";
import { navigate } from "../router.js";

export function loginView() {
  return {
    full: true,
    html: `
      <div class="auth-shell">
        <div class="auth-card">
          <h1>Entrar</h1>
          <div class="alert error" data-error style="display:none"></div>
          <form data-login-form>
            <label>E-mail
              <input type="email" name="email" required autocomplete="email" />
            </label>
            <label>Senha
              <input type="password" name="password" required autocomplete="current-password" />
            </label>
            <button class="btn primary" type="submit">Entrar</button>
          </form>
          <p class="muted center">Ainda não tem conta?
            <a href="#/auth/register">Cadastre-se</a>
          </p>
        </div>
      </div>
    `,
    mount({ container }) {
      const form = container.querySelector("[data-login-form]");
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        setError(container, "");
        const fd = new FormData(form);
        try {
          await login(fd.get("email"), fd.get("password"));
          navigate("/");
        } catch (err) {
          setError(container, err.message);
        }
      });
    },
  };
}

export function registerView() {
  return {
    full: true,
    html: `
      <div class="auth-shell">
        <div class="auth-card">
          <h1>Criar conta</h1>
          <div class="alert error" data-error style="display:none"></div>
          <form data-register-form>
            <label>Nome
              <input type="text" name="first_name" required />
            </label>
            <label>E-mail
              <input type="email" name="email" required autocomplete="email" />
            </label>
            <label>Senha
              <input type="password" name="password" required minlength="8" autocomplete="new-password" />
            </label>
            <label>Confirmar senha
              <input type="password" name="password_confirmation" required minlength="8" autocomplete="new-password" />
            </label>
            <button class="btn primary" type="submit">Cadastrar</button>
          </form>
          <p class="muted center">Já tem conta?
            <a href="#/auth/login">Entrar</a>
          </p>
        </div>
      </div>
    `,
    mount({ container }) {
      const form = container.querySelector("[data-register-form]");
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        setError(container, "");
        const fd = new FormData(form);
        const payload = {
          first_name: fd.get("first_name"),
          email: fd.get("email"),
          password: fd.get("password"),
          password_confirmation: fd.get("password_confirmation"),
        };
        if (form.querySelector('[name="last_name"]')) payload.last_name = fd.get("last_name");
        try {
          await register(payload);
          navigate("/");
        } catch (err) {
          setError(container, err.message);
        }
      });
    },
  };
}
