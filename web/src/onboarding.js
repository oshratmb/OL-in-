import {
  aiServiceFetch,
  getCurrentUserId,
  hasCompletedOnboarding,
  isAuthenticated,
  restoreSession,
  supabaseFetch,
} from "./apiClient.js";
import { logIn, logOut, signUp, startGoogleLogin, validatePassword } from "./auth.js";

const authStage = document.getElementById("auth-stage");
const uploadStage = document.getElementById("upload-stage");
const authForm = document.getElementById("auth-form");
const authError = document.getElementById("auth-error");
const nameField = document.getElementById("name-field");
const authSubmit = document.getElementById("auth-submit");
const tabs = document.querySelectorAll(".tab");
const progressFill = document.getElementById("progress-fill");

let mode = "signup";

function setMode(newMode) {
  mode = newMode;
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.mode === mode));
  nameField.classList.toggle("hidden", mode !== "signup");
  authSubmit.textContent = mode === "signup" ? "הרשמה" : "התחברות";
}

tabs.forEach((tab) => tab.addEventListener("click", () => setMode(tab.dataset.mode)));

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authError.classList.add("hidden");

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const name = document.getElementById("name").value.trim();

  if (mode === "signup") {
    const problems = validatePassword(password);
    if (problems.length) {
      showAuthError("הסיסמה חסרה: " + problems.join(", "));
      return;
    }
  }

  authSubmit.disabled = true;
  try {
    if (mode === "signup") {
      await signUp(email, password, name);
      showUploadStage();
    } else {
      const result = await logIn(email, password);
      if (result.status === "ok") {
        if (await hasCompletedOnboarding()) {
          window.location.href = "/dashboard.html";
        } else {
          showUploadStage();
        }
      } else {
        // A real page navigation to mfa.html means a fresh JS context — an
        // in-memory-only handoff isn't possible here the way it is for the
        // rest of this app's access tokens. sessionStorage is the least-bad
        // option: this specific token is short-lived, aal1-only, and mfa.js
        // deletes it from sessionStorage the instant it's read.
        sessionStorage.setItem(
          "pendingMfa",
          JSON.stringify({
            mode: result.status === "mfa_enrollment_required" ? "enroll" : "challenge",
            tempAccessToken: result.tempAccessToken,
            factorId: result.factorId,
          })
        );
        window.location.href = "/mfa.html";
      }
    }
  } catch (err) {
    showAuthError(err.message);
  } finally {
    authSubmit.disabled = false;
  }
});

document.getElementById("google-btn").addEventListener("click", startGoogleLogin);

document.getElementById("logout-btn").addEventListener("click", async () => {
  await logOut();
  uploadStage.classList.add("hidden");
  authStage.classList.remove("hidden");
  progressFill.style.width = "33%";
});

function showAuthError(message) {
  authError.textContent = message;
  authError.classList.remove("hidden");
}

function showUploadStage() {
  authStage.classList.add("hidden");
  uploadStage.classList.remove("hidden");
  progressFill.style.width = "66%";
}

// --- resume upload ---

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const uploadError = document.getElementById("upload-error");
const uploadStatus = document.getElementById("upload-status");

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) handleFile(fileInput.files[0]);
});

async function handleFile(file) {
  uploadError.classList.add("hidden");
  const validExt = /\.(pdf|docx)$/i.test(file.name);
  if (!validExt) {
    uploadError.textContent = "יש להעלות קובץ PDF או Word (.docx) בלבד";
    uploadError.classList.remove("hidden");
    return;
  }

  setStatus("מעלה קובץ...");
  try {
    const storagePath = await uploadResume(file);
    setStatus("מנתח את קורות החיים...");
    const parsedData = await parseResume(storagePath);
    sessionStorage.setItem(
      "pendingProfile",
      JSON.stringify({ storagePath, parsedData })
    );
    window.location.href = "/profile.html";
  } catch (err) {
    uploadError.textContent = err.message || "משהו השתבש, נסו שוב";
    uploadError.classList.remove("hidden");
    setStatus("");
  }
}

function setStatus(text) {
  if (!text) {
    uploadStatus.classList.add("hidden");
    return;
  }
  uploadStatus.textContent = text;
  uploadStatus.classList.remove("hidden");
}

async function uploadResume(file) {
  const userId = getCurrentUserId();
  const safeName = file.name.replace(/[^\w.\-]/g, "_");
  const path = `${userId}/${Date.now()}_${safeName}`;
  const res = await supabaseFetch(`/storage/v1/object/resumes/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
      "x-upsert": "true",
    },
    body: file,
  });
  if (!res.ok) throw new Error("העלאת הקובץ נכשלה");
  return path;
}

async function parseResume(storagePath) {
  const res = await aiServiceFetch("/parse-resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ storage_path: storagePath }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "ניתוח קורות החיים נכשל");
  return data.parsed_data;
}

// --- init: resume an existing session (e.g. after Google login redirect) ---

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) return;
  if (await hasCompletedOnboarding()) {
    window.location.href = "/dashboard.html";
  } else {
    showUploadStage();
  }
})();
