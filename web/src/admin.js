import { aiServiceFetch, isAuthenticated, restoreSession } from "./apiClient.js";

const deniedMessage = document.getElementById("denied-message");
const adminContent = document.getElementById("admin-content");
const kpiRow = document.getElementById("kpi-row");
const usersTableBody = document.getElementById("users-table-body");
const errorsTableBody = document.getElementById("errors-table-body");
const errorsCard = document.getElementById("errors-card");
const pauseColHeader = document.getElementById("pause-col-header");

let isSuperAdmin = false;

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

function renderStats(stats) {
  const tiles = [
    { label: "סך משתמשים", value: stats.total_users },
    { label: "התאמות קו״ח שבוצעו", value: stats.total_document_generations },
    { label: "סימולציות שהושלמו", value: stats.total_completed_simulations },
    { label: "שגיאות Gmail (24 שעות)", value: stats.gmail_sync_errors_24h },
  ];
  kpiRow.innerHTML = tiles
    .map((t) => `<div class="kpi-tile"><div class="value">${t.value}</div><div class="label">${t.label}</div></div>`)
    .join("");
}

function renderUsers(users) {
  usersTableBody.innerHTML = users
    .map(
      (u) => `
      <tr>
        <td>${escapeHtml(u.name || "-")}</td>
        <td>${escapeHtml(u.email || "-")}</td>
        <td>${escapeHtml(u.role)}</td>
        <td>${escapeHtml((u.created_at || "").slice(0, 10))}</td>
        <td><span class="badge ${u.is_paused ? "paused" : ""}">${u.is_paused ? "מושהה" : "פעיל"}</span></td>
        ${
          isSuperAdmin
            ? `<td><button type="button" class="btn-secondary pause-btn" data-user-id="${u.id}" data-paused="${u.is_paused}" style="width:auto; padding:4px 10px; font-size:0.8rem;">${u.is_paused ? "הפעל" : "השהה"}</button></td>`
            : ""
        }
      </tr>`
    )
    .join("");

  usersTableBody.querySelectorAll(".pause-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const paused = btn.dataset.paused !== "true";
      btn.disabled = true;
      await aiServiceFetch(`/admin/users/${btn.dataset.userId}/pause`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paused }),
      });
      await loadUsers();
    });
  });
}

function renderErrors(errors) {
  errorsTableBody.innerHTML = errors
    .map(
      (e) => `<tr><td>${escapeHtml(e.source)}</td><td>${escapeHtml(e.message)}</td><td>${escapeHtml((e.created_at || "").replace("T", " ").slice(0, 19))}</td></tr>`
    )
    .join("");
}

async function loadUsers(search) {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  const res = await aiServiceFetch(`/admin/users${query}`);
  if (res.ok) renderUsers(await res.json());
}

document.getElementById("user-search").addEventListener("input", (e) => {
  clearTimeout(window._searchDebounce);
  window._searchDebounce = setTimeout(() => loadUsers(e.target.value.trim()), 300);
});

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) {
    window.location.href = "/index.html";
    return;
  }

  const statsRes = await aiServiceFetch("/admin/stats");
  if (!statsRes.ok) {
    deniedMessage.classList.remove("hidden");
    setTimeout(() => (window.location.href = "/dashboard.html"), 2000);
    return;
  }
  renderStats(await statsRes.json());
  adminContent.classList.remove("hidden");

  await loadUsers();

  const errorsRes = await aiServiceFetch("/admin/errors");
  if (errorsRes.ok) {
    isSuperAdmin = true;
    pauseColHeader.classList.remove("hidden");
    errorsCard.classList.remove("hidden");
    renderErrors(await errorsRes.json());
    await loadUsers(); // re-render with the pause column now that we know we're super_admin
  }
})();
