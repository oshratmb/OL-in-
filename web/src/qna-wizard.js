import { aiServiceFetch, isAuthenticated, restoreSession } from "./apiClient.js";

const questionCard = document.getElementById("question-card");
const generatingCard = document.getElementById("generating-card");
const generateError = document.getElementById("generate-error");
const progressFill = document.getElementById("progress-fill");
const questionCounter = document.getElementById("question-counter");
const questionText = document.getElementById("question-text");
const answerInput = document.getElementById("answer-input");
const skipTip = document.getElementById("skip-tip");
const nextBtn = document.getElementById("next-btn");
const skipBtn = document.getElementById("skip-btn");

let job = null;
let questions = [];
let index = 0;
const answers = [];

function showQuestion() {
  skipTip.classList.add("hidden");
  answerInput.value = "";
  const q = questions[index];
  questionCounter.textContent = `שאלה ${index + 1} מתוך ${questions.length}`;
  questionText.textContent = q.question;
  progressFill.style.width = `${(index / questions.length) * 100}%`;
}

function recordAnswer(answerText) {
  const q = questions[index];
  answers.push({ question_id: q.id, question: q.question, answer: answerText });
  index += 1;
  if (index < questions.length) {
    showQuestion();
  } else {
    generateDocuments();
  }
}

nextBtn.addEventListener("click", () => recordAnswer(answerInput.value.trim()));

skipBtn.addEventListener("click", () => {
  skipTip.classList.remove("hidden");
  nextBtn.disabled = true;
  skipBtn.disabled = true;
  setTimeout(() => {
    nextBtn.disabled = false;
    skipBtn.disabled = false;
    recordAnswer("");
  }, 1400);
});

async function generateDocuments() {
  questionCard.classList.add("hidden");
  generatingCard.classList.remove("hidden");

  try {
    const res = await aiServiceFetch("/documents/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job, qna_answers: answers, tone: "professional" }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "יצירת המסמכים נכשלה");

    sessionStorage.setItem("documentResult", JSON.stringify({ ...data, job, qna_answers: answers }));
    sessionStorage.removeItem("pendingJob");
    window.location.href = "/document-preview.html";
  } catch (err) {
    generatingCard.classList.add("hidden");
    generateError.textContent = err.message;
    generateError.classList.remove("hidden");
  }
}

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) {
    window.location.href = "/index.html";
    return;
  }

  const pending = JSON.parse(sessionStorage.getItem("pendingJob") || "null");
  if (!pending) {
    window.location.href = "/job-intake.html";
    return;
  }
  job = pending.job;
  questions = pending.gapQuestions || [];

  if (questions.length === 0) {
    generateDocuments();
  } else {
    showQuestion();
  }
})();
