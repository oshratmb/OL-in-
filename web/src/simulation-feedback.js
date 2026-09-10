import { aiServiceFetch, isAuthenticated, restoreSession } from "./apiClient.js";

const params = new URLSearchParams(window.location.search);
const simulationId = params.get("simulation_id");

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".tab-panel");
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.toggle("active", t === tab));
    panels.forEach((p) => p.classList.toggle("active", p.id === `panel-${tab.dataset.tab}`));
  });
});

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

function renderList(elementId, items) {
  const el = document.getElementById(elementId);
  el.innerHTML = items.length
    ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : '<li class="hint-text">אין נתונים</li>';
}

function renderGauge(score) {
  const color = score >= 70 ? "var(--success)" : score >= 40 ? "#e0a52c" : "var(--danger)";
  document.getElementById("gauge").style.background = `conic-gradient(${color} ${score}%, var(--border) 0)`;
  document.getElementById("score-number").textContent = score;
}

function renderRewriteTab(perQuestion) {
  const el = document.getElementById("panel-rewrite");
  el.innerHTML = perQuestion
    .map(
      (q) => `
      <div class="qa-block">
        <p class="label">שאלה</p>
        <p>${escapeHtml(q.question)}</p>
        <p class="label">התשובה שלכם</p>
        <p>${escapeHtml(q.answer)}</p>
        <p class="label">משוב</p>
        <p>${escapeHtml(q.feedback)}</p>
        <p class="label">הצעה לניסוח חלופי</p>
        <p><strong>${escapeHtml(q.suggested_answer)}</strong></p>
      </div>`
    )
    .join("");
}

function render(simulation) {
  const report = simulation.feedback_report;
  if (!report) return;
  renderGauge(report.overall_score);
  document.getElementById("summary-text").textContent = report.summary;
  renderList("panel-strengths", report.strengths);
  renderList("panel-improvements", report.improvements);
  renderRewriteTab(report.per_question);

  document.getElementById("restart-btn").dataset.applicationId = simulation.application_id;
}

document.getElementById("restart-btn").addEventListener("click", async (event) => {
  const applicationId = event.currentTarget.dataset.applicationId;
  window.location.href = `/interview-simulator.html?application_id=${applicationId}`;
});

document.getElementById("back-btn").addEventListener("click", () => {
  window.location.href = "/dashboard.html";
});

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) {
    window.location.href = "/index.html";
    return;
  }
  if (!simulationId) {
    window.location.href = "/dashboard.html";
    return;
  }

  const res = await aiServiceFetch(`/simulations/${simulationId}`);
  if (!res.ok) {
    window.location.href = "/dashboard.html";
    return;
  }
  render(await res.json());
})();
