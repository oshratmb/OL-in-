import { aiServiceFetch, hasCompletedOnboarding, setAccessToken } from "./apiClient.js";

const pending = JSON.parse(sessionStorage.getItem("pendingMfa") || "null");
sessionStorage.removeItem("pendingMfa"); // read once, then gone — see onboarding.js's comment

const errorEl = document.getElementById("mfa-error");
const confirmBtn = document.getElementById("confirm-btn");
let factorId = pending?.factorId || null;

function showError(message) {
  errorEl.textContent = message;
  errorEl.classList.remove("hidden");
}

async function goToApp() {
  window.location.href = (await hasCompletedOnboarding()) ? "/dashboard.html" : "/index.html";
}

async function setupEnrollment() {
  document.getElementById("mfa-title").textContent = "הפעילו אימות דו-שלבי";
  document.getElementById("mfa-subtitle").textContent =
    "כמנהל/ת על, נדרש אימות דו-שלבי. סרקו את הקוד עם אפליקציית Authenticator (כגון Google Authenticator).";
  document.getElementById("enroll-section").classList.remove("hidden");

  const res = await aiServiceFetch("/auth/mfa/enroll", { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    showError(data.detail || "שגיאה בהפעלת האימות הדו-שלבי");
    return;
  }
  factorId = data.factor_id;
  document.getElementById("qr-image").src = data.qr_code;
  document.getElementById("secret-text").textContent = data.secret;
}

function setupChallenge() {
  document.getElementById("mfa-title").textContent = "אימות דו-שלבי";
  document.getElementById("mfa-subtitle").textContent = "הזינו את הקוד מאפליקציית ה-Authenticator שלכם.";
}

confirmBtn.addEventListener("click", async () => {
  const code = document.getElementById("code-input").value.trim();
  if (!code || !factorId) {
    showError("יש להזין קוד בן 6 ספרות");
    return;
  }

  confirmBtn.disabled = true;
  errorEl.classList.add("hidden");
  try {
    const path = pending.mode === "enroll" ? "/auth/mfa/verify-enroll" : "/auth/mfa/verify";
    const body = pending.mode === "enroll" ? { factor_id: factorId, code } : await withChallenge(factorId, code);

    const res = await aiServiceFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "הקוד שגוי, נסו שוב");

    setAccessToken(data.access_token);
    await goToApp();
  } catch (err) {
    showError(err.message);
    confirmBtn.disabled = false;
  }
});

async function withChallenge(factor_id, code) {
  const res = await aiServiceFetch("/auth/mfa/challenge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ factor_id }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "שגיאה ביצירת אתגר האימות");
  return { factor_id, challenge_id: data.challenge_id, code };
}

(function init() {
  if (!pending?.tempAccessToken) {
    window.location.href = "/index.html";
    return;
  }
  setAccessToken(pending.tempAccessToken);

  if (pending.mode === "enroll") {
    setupEnrollment();
  } else {
    setupChallenge();
  }
})();
