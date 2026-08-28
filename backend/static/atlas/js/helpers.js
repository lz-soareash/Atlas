// Utilidades compartilhadas do frontend.

// Escapa texto para evitar injeção de HTML (XSS).
export function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Cria um elemento a partir de uma string HTML.
export function create(html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = html.trim();
  return tpl.content.firstElementChild;
}

// Mostra/oculta erro em um campo de formulário.
export function setError(el, message) {
  const box = el.querySelector("[data-error]");
  if (!box) return;
  if (message) {
    box.textContent = message;
    box.style.display = "block";
  } else {
    box.textContent = "";
    box.style.display = "none";
  }
}
