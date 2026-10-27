// Shared front-end helpers for the mock application.
const API = {
  token() { return sessionStorage.getItem("token"); },
  user() { try { return JSON.parse(sessionStorage.getItem("user") || "null"); } catch (e) { return null; } },
  async call(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (this.token()) headers.Authorization = "Bearer " + this.token();
    const res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    let data = {};
    try { data = await res.json(); } catch (e) { /* non-JSON */ }
    if (res.status === 401 && !path.startsWith("/api/auth/")) {
      sessionStorage.clear();
      location.href = "login.html";
    }
    return { ok: res.ok, status: res.status, data };
  },
  get(p) { return this.call("GET", p); },
  post(p, b) { return this.call("POST", p, b || {}); },
  put(p, b) { return this.call("PUT", p, b || {}); },
  del(p) { return this.call("DELETE", p); },
};

function $(sel, root) { return (root || document).querySelector(sel); }
function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([k, v]) => {
    if (k === "testid") node.dataset.testid = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) node.setAttribute(k, v);
  });
  children.flat().forEach(c => node.append(c instanceof Node ? c : document.createTextNode(c ?? "")));
  return node;
}

function toast(message, type) {
  let t = document.querySelector('[data-testid="toast"]');
  if (!t) { t = el("div", { testid: "toast", role: "status" }); document.body.append(t); }
  t.className = "toast " + (type || "success");
  t.textContent = message;
}

function clearErrors(form) {
  form.querySelectorAll(".field-error").forEach(e => { e.textContent = ""; });
}

function showError(field, message) {
  const node = document.querySelector(`[data-testid="error-${field}"]`);
  if (node) node.textContent = message; else toast(message, "error");
}

function requireAuth() {
  if (!API.token()) { location.href = "login.html"; return false; }
  return true;
}

function renderShell(active, links, brand) {
  const user = API.user() || {};
  const nav = el("nav", { class: "topnav" },
    el("span", { class: "brand" }, brand),
    ...links.map(([id, label, href]) =>
      el("a", { href, testid: "nav-" + id, class: id === active ? "active" : "" }, label)),
    el("span", { class: "spacer" }),
    el("span", { testid: "user-badge", class: "badge" }, user.display_name || user.username || ""),
    el("button", { testid: "logout", class: "link", onclick: () => { sessionStorage.clear(); location.href = "login.html"; } }, "Logout"));
  document.body.prepend(nav);
}

function money(value, currency) {
  const symbols = { GBP: "£", USD: "$", EUR: "€", SEK: "kr", NOK: "kr", DKK: "kr" };
  const n = Number(value).toFixed(2);
  const sym = symbols[currency] || "";
  return ["SEK", "NOK", "DKK"].includes(currency) ? `${n} ${sym}` : `${sym}${n}`;
}
