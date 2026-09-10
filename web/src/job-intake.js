import { aiServiceFetch, isAuthenticated, restoreSession } from "./apiClient.js";

const analyzeBtn = document.getElementById("analyze-btn");
const analyzeError = document.getElementById("analyze-error");
const resultsCard = document.getElementById("results-card");
const matchFill = document.getElementById("match-fill");
const matchLabel = document.getElementById("match-label");
const requirementsList = document.getElementById("requirements-list");

let lastAnalysis = null;
let descriptionText = "";

analyzeBtn.addEventListener("click", async () => {
  analyzeError.classList.add("hidden");
  descriptionText = document.getElementById("jd-text").value.trim();
  if (!descriptionText) {
    showError("יש להדביק תיאור משרה לפני הניתוח");
    return;
  }

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "מנתח...";
  try {
    const res = await aiServiceFetch("/jobs/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description_text: descriptionText }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "הניתוח נכשל");
    lastAnalysis = data;
    renderResults(data);
  } catch (err) {
    showError(err.message);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "נתח משרה";
  }
});

function showError(message) {
  analyzeError.textContent = message;
  analyzeError.classList.remove("hidden");
}

function renderResults(data) {
  document.getElementById("job-title").value = data.detected_title || "";
  document.getElementById("company-name").value = data.detected_company_name || "";

  const pct = Math.max(0, Math.min(100, data.match_percentage || 0));
  matchFill.style.width = `${pct}%`;
  matchFill.style.background = pct >= 70 ? "var(--success)" : pct >= 40 ? "#e0a52c" : "var(--danger)";
  matchLabel.textContent = `${pct}% התאמה`;

  requirementsList.innerHTML = "";
  for (const req of data.requirements || []) {
    const li = document.createElement("li");
    li.style.color = req.present ? "var(--success)" : "var(--danger)";
    li.textContent = `${req.present ? "✓" : "✗"} ${req.requirement}${req.note ? " — " + req.note : ""}`;
    requirementsList.appendChild(li);
  }

  resultsCard.classList.remove("hidden");
}

document.getElementById("continue-btn").addEventListener("click", () => {
  const job = {
    title: document.getElementById("job-title").value.trim(),
    company_name: document.getElementById("company-name").value.trim(),
    description_text: descriptionText,
  };
  sessionStorage.setItem(
    "pendingJob",
    JSON.stringify({ job, gapQuestions: lastAnalysis?.gap_questions || [] })
  );
  window.location.href = "/qna-wizard.html";
});

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) window.location.href = "/index.html";
})();
