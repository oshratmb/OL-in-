import { aiServiceFetch, isAuthenticated, restoreSession, supabaseFetch } from "./apiClient.js";
import { logOut } from "./auth.js";

const STATUS_LABELS = {
  applied: "הוגש",
  phone_screen: "ראיון טלפוני",
  homework: "משימת בית",
  tech_interview: "ראיון טכנולוגי",
  offer: "הצעת חוזה",
  rejected: "נדחה",
  on_hold: "מוקפא",
};

const COLUMNS = [
  { label: "הוגש", statuses: ["applied"] },
  { label: "ראיון טלפוני", statuses: ["phone_screen"] },
  { label: "משימת בית", statuses: ["homework"] },
  { label: "ראיון טכנולוגי", statuses: ["tech_interview"] },
  { label: "הצעת חוזה", statuses: ["offer"] },
  { label: "דחייה / הוקפא", statuses: ["rejected", "on_hold"] },
];

const board = document.getElementById("board");

function initials(text) {
  return (text || "?").trim().slice(0, 2).toUpperCase();
}

function statusSelect(applicationId, currentStatus) {
  const select = document.createElement("select");
  for (const [value, label] of Object.entries(STATUS_LABELS)) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === currentStatus;
    select.appendChild(option);
  }
  select.addEventListener("change", async () => {
    await supabaseFetch(`/rest/v1/applications?id=eq.${applicationId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: select.value }),
    });
    loadBoard();
  });
  return select;
}

function renderCard(app) {
  const card = document.createElement("div");
  card.className = "job-card";

  const titleRow = document.createElement("div");
  titleRow.className = "title-row";
  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.textContent = initials(app.jobs?.company_name);
  const title = document.createElement("strong");
  title.textContent = app.jobs?.title || "";
  titleRow.append(avatar, title);

  const company = document.createElement("p");
  company.className = "company";
  company.textContent = `${app.jobs?.company_name || ""} · ${(app.applied_at || "").slice(0, 10)}`;

  card.append(titleRow, company, statusSelect(app.id, app.status));

  if (["phone_screen", "tech_interview"].includes(app.status)) {
    const prepBtn = document.createElement("a");
    prepBtn.href = `/interview-simulator.html?application_id=${app.id}`;
    prepBtn.className = "btn-secondary";
    prepBtn.style.cssText = "display:block; text-align:center; text-decoration:none; margin-top:8px; padding:6px;";
    prepBtn.style.fontSize = "0.8rem";
    prepBtn.textContent = "התחל הכנה לראיון";
    card.appendChild(prepBtn);
  }

  return card;
}

async function loadBoard() {
  const res = await supabaseFetch(
    "/rest/v1/applications?select=id,status,applied_at,jobs(title,company_name)&order=applied_at.desc"
  );
  const applications = res.ok ? await res.json() : [];

  board.innerHTML = "";
  for (const column of COLUMNS) {
    const columnEl = document.createElement("div");
    columnEl.className = "column";
    const heading = document.createElement("h3");
    heading.textContent = column.label;
    columnEl.appendChild(heading);

    const items = applications.filter((a) => column.statuses.includes(a.status));
    if (items.length === 0) {
      const empty = document.createElement("p");
      empty.className = "hint-text";
      empty.textContent = "אין משרות";
      columnEl.appendChild(empty);
    } else {
      for (const app of items) columnEl.appendChild(renderCard(app));
    }
    board.appendChild(columnEl);
  }
}

async function loadUnlinkedEmails() {
  const banner = document.getElementById("unlinked-banner");
  const list = document.getElementById("unlinked-list");
  const res = await aiServiceFetch("/emails/unlinked");
  const emails = res.ok ? await res.json() : [];

  if (emails.length === 0) {
    banner.classList.add("hidden");
    return;
  }

  list.innerHTML = "";
  for (const email of emails) {
    const item = document.createElement("div");
    item.className = "unlinked-item";
    const label = document.createElement("p");
    label.style.margin = "0 0 6px";
    label.innerHTML = `<strong>${escapeHtml(email.sender)}</strong>: ${escapeHtml(email.subject)}`;
    item.appendChild(label);

    for (const candidate of email.candidates) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "candidate-btn";
      btn.textContent = `${candidate.job_title} — ${candidate.company_name}`;
      btn.addEventListener("click", async () => {
        await aiServiceFetch(`/emails/${email.id}/link`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ application_id: candidate.application_id }),
        });
        await Promise.all([loadUnlinkedEmails(), loadBoard()]);
      });
      item.appendChild(btn);
    }
    list.appendChild(item);
  }
  banner.classList.remove("hidden");
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

const syncBtn = document.getElementById("sync-btn");
const syncStatus = document.getElementById("sync-status");

syncBtn.addEventListener("click", async () => {
  syncBtn.disabled = true;
  syncStatus.textContent = "מסנכרן...";
  syncStatus.classList.remove("hidden");
  try {
    const res = await aiServiceFetch("/gmail/sync-now", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "הסנכרון נכשל");
    syncStatus.textContent = "הסנכרון הושלם";
    await Promise.all([loadUnlinkedEmails(), loadBoard()]);
  } catch (err) {
    syncStatus.textContent = err.message;
  } finally {
    syncBtn.disabled = false;
    setTimeout(() => syncStatus.classList.add("hidden"), 3000);
  }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  await logOut();
  window.location.href = "/index.html";
});

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) {
    window.location.href = "/index.html";
    return;
  }
  await Promise.all([loadBoard(), loadUnlinkedEmails()]);
})();
