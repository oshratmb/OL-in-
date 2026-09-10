import { aiServiceFetch, getCurrentUserId, isAuthenticated, restoreSession, supabaseFetch } from "./apiClient.js";

const statusText = document.getElementById("gmail-status-text");
const connectBtn = document.getElementById("gmail-connect-btn");
const disconnectBtn = document.getElementById("gmail-disconnect-btn");
const reconnectNote = document.getElementById("gmail-reconnect");
const gmailError = document.getElementById("gmail-error");

async function loadGmailStatus() {
  const res = await aiServiceFetch("/gmail/status");
  const data = await res.json();

  reconnectNote.classList.toggle("hidden", !data.needs_reconnect);

  if (data.connected) {
    statusText.textContent = `מחובר כ-${data.google_email || ""}`;
    connectBtn.classList.add("hidden");
    disconnectBtn.classList.remove("hidden");
  } else {
    statusText.textContent = "Gmail אינו מחובר";
    connectBtn.classList.remove("hidden");
    disconnectBtn.classList.add("hidden");
  }
}

connectBtn.addEventListener("click", async () => {
  const res = await aiServiceFetch("/gmail/connect/start", { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    gmailError.classList.remove("hidden");
    return;
  }
  window.location.href = data.authorize_url;
});

disconnectBtn.addEventListener("click", async () => {
  await aiServiceFetch("/gmail/disconnect", { method: "POST" });
  await loadGmailStatus();
});

const manualError = document.getElementById("manual-error");
const manualSuccess = document.getElementById("manual-success");
const manualBtn = document.getElementById("manual-submit-btn");

manualBtn.addEventListener("click", async () => {
  manualError.classList.add("hidden");
  manualSuccess.classList.add("hidden");

  const sender = document.getElementById("m-sender").value.trim();
  const subject = document.getElementById("m-subject").value.trim();
  const body_content = document.getElementById("m-body").value.trim();
  if (!sender || !body_content) {
    manualError.textContent = "יש למלא לפחות שולח ותוכן מייל";
    manualError.classList.remove("hidden");
    return;
  }

  manualBtn.disabled = true;
  try {
    const res = await aiServiceFetch("/emails/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender, subject, body_content }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "הניתוח נכשל");
    manualSuccess.classList.remove("hidden");
    document.getElementById("m-sender").value = "";
    document.getElementById("m-subject").value = "";
    document.getElementById("m-body").value = "";
  } catch (err) {
    manualError.textContent = err.message;
    manualError.classList.remove("hidden");
  } finally {
    manualBtn.disabled = false;
  }
});

document.getElementById("back-btn").addEventListener("click", () => {
  window.location.href = "/dashboard.html";
});

const pauseStatusText = document.getElementById("pause-status-text");
const pauseToggleBtn = document.getElementById("pause-toggle-btn");
let isPaused = false;

async function loadPauseStatus() {
  const res = await supabaseFetch(`/rest/v1/profiles?id=eq.${getCurrentUserId()}&select=is_paused&limit=1`);
  if (!res.ok) return;
  const rows = await res.json();
  isPaused = rows[0]?.is_paused ?? false;
  renderPauseState();
}

function renderPauseState() {
  pauseToggleBtn.textContent = isPaused ? "הפעל חשבון מחדש" : "השהה חשבון";
  pauseToggleBtn.className = isPaused ? "btn-primary" : "btn-danger";
}

pauseToggleBtn.addEventListener("click", async () => {
  pauseToggleBtn.disabled = true;
  try {
    await aiServiceFetch(isPaused ? "/account/resume" : "/account/pause", { method: "POST" });
    isPaused = !isPaused;
    renderPauseState();
  } finally {
    pauseToggleBtn.disabled = false;
  }
});

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) {
    window.location.href = "/index.html";
    return;
  }

  const params = new URLSearchParams(window.location.search);
  if (params.get("gmail_error")) gmailError.classList.remove("hidden");
  history.replaceState(null, "", window.location.pathname);

  await Promise.all([loadGmailStatus(), loadPauseStatus()]);
})();
