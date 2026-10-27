const BRAND = "CareCycle RCM";
const ALL_LINKS = [["patients", "Patients", "patients.html"], ["providers", "Providers", "providers.html"],
  ["encounters", "Encounters", "encounters.html"], ["dashboard", "Provider Dashboard", "dashboard.html"], ["claims", "Claims", "claims.html"]];
const ROLE_ACCESS = { ADMIN: ["patients", "providers", "encounters", "claims", "dashboard"],
  FRONT_DESK: ["patients", "encounters"], PROVIDER: ["dashboard", "encounters", "patients"] };
function allowed(area) { const u = API.user(); return !!u && ROLE_ACCESS[u.role].includes(area); }
function shell(active) {
  if (!requireAuth()) return false;
  renderShell(active, ALL_LINKS.filter(l => allowed(l[0])), BRAND);
  if (active && !allowed(active)) {
    document.querySelector("main").innerHTML = '<div class="card" data-testid="access-denied"><h1>Access denied</h1><p>You do not have permission to access this module.</p></div>';
    return false;
  }
  return true;
}
function homeFor(role) { return role === "PROVIDER" ? "dashboard.html" : "patients.html"; }
function formData(form) { const o = {}; new FormData(form).forEach((v, k) => o[k] = typeof v === "string" ? v.trim() : v); return o; }
