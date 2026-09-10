import { aiServiceFetch, isAuthenticated, restoreSession } from "./apiClient.js";

let data = null;

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".tab-panel");
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.toggle("active", t === tab));
    panels.forEach((p) => p.classList.toggle("active", p.id === `panel-${tab.dataset.tab}`));
  });
});

function renderResume(resume) {
  const el = document.getElementById("resume-preview");
  const personal = resume.personal_info || {};
  const parts = [];
  parts.push(`<h2>${escapeHtml(personal.name || "")}</h2>`);
  parts.push(
    `<p class="hint-text">${[personal.email, personal.phone, personal.location].filter(Boolean).map(escapeHtml).join(" | ")}</p>`
  );
  if (resume.professional_summary) parts.push(`<p>${escapeHtml(resume.professional_summary)}</p>`);

  if ((resume.work_experience || []).length) {
    parts.push("<h2>ניסיון תעסוקתי</h2>");
    for (const e of resume.work_experience) {
      parts.push(`<p><strong>${escapeHtml(e.title)} — ${escapeHtml(e.company)}</strong> (${escapeHtml(e.start_date)} - ${escapeHtml(e.end_date)})</p>`);
      parts.push("<ul>" + (e.bullets || []).map((b) => `<li>${escapeHtml(b)}</li>`).join("") + "</ul>");
    }
  }

  if ((resume.education || []).length) {
    parts.push("<h2>השכלה</h2>");
    for (const e of resume.education) {
      parts.push(`<p>${[e.degree, e.field, e.institution, e.year].filter(Boolean).map(escapeHtml).join(" - ")}</p>`);
    }
  }

  if ((resume.skills || []).length) {
    parts.push(`<h2>מיומנויות</h2><p>${resume.skills.map(escapeHtml).join(", ")}</p>`);
  }

  el.innerHTML = parts.join("");
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

function renderTrustWarning() {
  const banner = document.getElementById("trust-warning");
  if (data.gatekeeper_status !== "TRUST_WARNING") {
    banner.classList.add("hidden");
    return;
  }
  const list = document.getElementById("violations-list");
  list.innerHTML = (data.violations || []).map((v) => `<li>${escapeHtml(v)}</li>`).join("");
  banner.classList.remove("hidden");
}

function render() {
  renderResume(data.resume);
  document.getElementById("cover-letter-text").textContent = data.cover_letter_text;
  renderTrustWarning();
}

document.getElementById("download-btn").addEventListener("click", () => {
  window.open(data.tailored_resume_url, "_blank");
});

document.getElementById("copy-btn").addEventListener("click", async () => {
  await navigator.clipboard.writeText(data.cover_letter_text);
  const btn = document.getElementById("copy-btn");
  const original = btn.textContent;
  btn.textContent = "הועתק!";
  setTimeout(() => (btn.textContent = original), 1500);
});

const actionError = document.getElementById("action-error");

document.getElementById("tone-select").addEventListener("change", async (event) => {
  await withErrorHandling(async () => {
    const res = await aiServiceFetch("/documents/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job: data.job,
        qna_answers: data.qna_answers,
        tone: event.target.value,
        application_id: data.application_id,
      }),
    });
    const updated = await res.json();
    if (!res.ok) throw new Error(updated.detail || "עדכון הטון נכשל");
    data = { ...data, ...updated };
    persist();
    render();
  });
});

document.getElementById("lang-toggle").addEventListener("click", async () => {
  const target = document.getElementById("lang-toggle").dataset.lang === "en" ? "he" : "en";
  await withErrorHandling(async () => {
    const res = await aiServiceFetch("/documents/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        application_id: data.application_id,
        resume: data.resume,
        cover_letter_text: data.cover_letter_text,
        target_language: target,
      }),
    });
    const updated = await res.json();
    if (!res.ok) throw new Error(updated.detail || "התרגום נכשל");
    data = { ...data, ...updated };
    persist();
    render();
    const btn = document.getElementById("lang-toggle");
    btn.dataset.lang = target;
    btn.textContent = target === "en" ? "תרגם לעברית" : "תרגם לאנגלית";
  });
});

async function withErrorHandling(fn) {
  actionError.classList.add("hidden");
  try {
    await fn();
  } catch (err) {
    actionError.textContent = err.message;
    actionError.classList.remove("hidden");
  }
}

function persist() {
  sessionStorage.setItem("documentResult", JSON.stringify(data));
}

document.getElementById("back-btn").addEventListener("click", () => {
  sessionStorage.removeItem("documentResult");
  window.location.href = "/dashboard.html";
});

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) {
    window.location.href = "/index.html";
    return;
  }

  data = JSON.parse(sessionStorage.getItem("documentResult") || "null");
  if (!data) {
    window.location.href = "/dashboard.html";
    return;
  }
  render();
})();
