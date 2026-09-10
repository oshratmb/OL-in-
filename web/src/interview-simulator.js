import { aiServiceFetch, isAuthenticated, restoreSession, supabaseFetch } from "./apiClient.js";

const params = new URLSearchParams(window.location.search);
const applicationId = params.get("application_id");

const chatFeed = document.getElementById("chat-feed");
const answerInput = document.getElementById("answer-input");
const sendBtn = document.getElementById("send-btn");
const finishBtn = document.getElementById("finish-btn");
const simError = document.getElementById("sim-error");

let simulationId = null;
let interviewDone = false;

function appendMessage(role, content) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = content;
  chatFeed.appendChild(el);
  chatFeed.scrollTop = chatFeed.scrollHeight;
}

function showError(message) {
  simError.textContent = message;
  simError.classList.remove("hidden");
}

function setDone() {
  interviewDone = true;
  answerInput.disabled = true;
  sendBtn.disabled = true;
  appendMessage("assistant", "הראיון הסתיים — לחצו על 'סיום הראיון וקבלת משוב' כדי לראות את המשוב שלכם.");
}

sendBtn.addEventListener("click", async () => {
  const text = answerInput.value.trim();
  if (!text || !simulationId) return;

  appendMessage("user", text);
  answerInput.value = "";
  sendBtn.disabled = true;

  const typing = document.createElement("div");
  typing.className = "msg assistant hint-text";
  typing.textContent = "מקליד...";
  chatFeed.appendChild(typing);
  chatFeed.scrollTop = chatFeed.scrollHeight;

  try {
    const res = await aiServiceFetch(`/simulations/${simulationId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: text }),
    });
    const data = await res.json();
    typing.remove();
    if (!res.ok) throw new Error(data.detail || "שליחת התשובה נכשלה");

    if (data.done) {
      setDone();
    } else {
      appendMessage("assistant", data.question);
    }
  } catch (err) {
    typing.remove();
    showError(err.message);
  } finally {
    sendBtn.disabled = interviewDone;
  }
});

answerInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendBtn.click();
  }
});

finishBtn.addEventListener("click", async () => {
  if (!simulationId) return;
  finishBtn.disabled = true;
  finishBtn.textContent = "מכין משוב...";
  try {
    const res = await aiServiceFetch(`/simulations/${simulationId}/feedback`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "הפקת המשוב נכשלה");
    window.location.href = `/simulation-feedback.html?simulation_id=${simulationId}`;
  } catch (err) {
    showError(err.message);
    finishBtn.disabled = false;
    finishBtn.textContent = "סיום הראיון וקבלת משוב";
  }
});

function startTimer() {
  const start = Date.now();
  setInterval(() => {
    const elapsed = Math.floor((Date.now() - start) / 1000);
    const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const seconds = String(elapsed % 60).padStart(2, "0");
    document.getElementById("timer").textContent = `${minutes}:${seconds}`;
  }, 1000);
}

async function loadJobInfo() {
  const res = await supabaseFetch(
    `/rest/v1/applications?id=eq.${applicationId}&select=jobs(title,company_name)&limit=1`
  );
  if (!res.ok) return;
  const rows = await res.json();
  const job = rows[0]?.jobs;
  if (job) {
    document.getElementById("job-title").textContent = job.title;
    document.getElementById("company-name").textContent = job.company_name;
  }
}

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) {
    window.location.href = "/index.html";
    return;
  }
  if (!applicationId) {
    window.location.href = "/dashboard.html";
    return;
  }

  await loadJobInfo();
  startTimer();

  try {
    const res = await aiServiceFetch("/simulations/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ application_id: applicationId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "התחלת הסימולציה נכשלה");

    simulationId = data.simulation_id;
    document.getElementById("persona-title").textContent = data.persona_role_title;
    appendMessage("assistant", data.question);
  } catch (err) {
    showError(err.message);
  }
})();
