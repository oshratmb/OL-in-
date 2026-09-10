import { getCurrentUserId, isAuthenticated, restoreSession, supabaseFetch } from "./apiClient.js";

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".tab-panel");
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.toggle("active", t === tab));
    panels.forEach((p) => p.classList.toggle("active", p.id === `panel-${tab.dataset.tab}`));
  });
});

const experienceList = document.getElementById("experience-list");
const educationList = document.getElementById("education-list");
const projectsList = document.getElementById("projects-list");

function addRemoveHandler(block) {
  block.querySelector(".entry-remove").addEventListener("click", () => block.remove());
}

function addExperienceEntry(entry = {}) {
  const block = document.createElement("div");
  block.className = "entry-block";
  block.innerHTML = `
    <button type="button" class="entry-remove">✕</button>
    <label>חברה</label><input type="text" class="exp-company" value="${escapeAttr(entry.company)}" />
    <label>תפקיד</label><input type="text" class="exp-title" value="${escapeAttr(entry.title)}" />
    <div style="display:flex; gap:10px;">
      <div style="flex:1"><label>מתאריך</label><input type="text" class="exp-start" value="${escapeAttr(entry.start_date)}" /></div>
      <div style="flex:1"><label>עד תאריך</label><input type="text" class="exp-end" value="${escapeAttr(entry.end_date)}" /></div>
    </div>
    <label>הישגים ותחומי אחריות (שורה לכל נקודה)</label>
    <textarea class="exp-bullets">${escapeText((entry.bullets || []).join("\n"))}</textarea>
  `;
  addRemoveHandler(block);
  experienceList.appendChild(block);
}

function addEducationEntry(entry = {}) {
  const block = document.createElement("div");
  block.className = "entry-block";
  block.innerHTML = `
    <button type="button" class="entry-remove">✕</button>
    <label>מוסד לימודים</label><input type="text" class="edu-institution" value="${escapeAttr(entry.institution)}" />
    <label>תואר</label><input type="text" class="edu-degree" value="${escapeAttr(entry.degree)}" />
    <label>תחום</label><input type="text" class="edu-field" value="${escapeAttr(entry.field)}" />
    <label>שנה</label><input type="text" class="edu-year" value="${escapeAttr(entry.year)}" />
  `;
  addRemoveHandler(block);
  educationList.appendChild(block);
}

function addProjectEntry(entry = {}) {
  const block = document.createElement("div");
  block.className = "entry-block";
  block.innerHTML = `
    <button type="button" class="entry-remove">✕</button>
    <label>שם הפרויקט</label><input type="text" class="proj-name" value="${escapeAttr(entry.name)}" />
    <label>תיאור</label><textarea class="proj-description">${escapeText(entry.description)}</textarea>
  `;
  addRemoveHandler(block);
  projectsList.appendChild(block);
}

function escapeAttr(value) {
  return String(value ?? "").replace(/"/g, "&quot;");
}
function escapeText(value) {
  return String(value ?? "").replace(/</g, "&lt;");
}

document.getElementById("add-experience").addEventListener("click", () => addExperienceEntry());
document.getElementById("add-education").addEventListener("click", () => addEducationEntry());
document.getElementById("add-project").addEventListener("click", () => addProjectEntry());

function collectExperience() {
  return [...experienceList.querySelectorAll(".entry-block")].map((block) => ({
    company: block.querySelector(".exp-company").value.trim(),
    title: block.querySelector(".exp-title").value.trim(),
    start_date: block.querySelector(".exp-start").value.trim(),
    end_date: block.querySelector(".exp-end").value.trim(),
    bullets: block
      .querySelector(".exp-bullets")
      .value.split("\n")
      .map((s) => s.trim())
      .filter(Boolean),
  }));
}

function collectEducation() {
  return [...educationList.querySelectorAll(".entry-block")].map((block) => ({
    institution: block.querySelector(".edu-institution").value.trim(),
    degree: block.querySelector(".edu-degree").value.trim(),
    field: block.querySelector(".edu-field").value.trim(),
    year: block.querySelector(".edu-year").value.trim(),
  }));
}

function collectProjects() {
  return [...projectsList.querySelectorAll(".entry-block")].map((block) => ({
    name: block.querySelector(".proj-name").value.trim(),
    description: block.querySelector(".proj-description").value.trim(),
  }));
}

function splitCommaList(value) {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function populateForm(parsed) {
  const personal = parsed.personal_info || {};
  document.getElementById("p-name").value = personal.name || "";
  document.getElementById("p-email").value = personal.email || "";
  document.getElementById("p-phone").value = personal.phone || "";
  document.getElementById("p-location").value = personal.location || "";
  document.getElementById("p-summary").value = parsed.professional_summary || "";
  document.getElementById("p-skills").value = (parsed.skills || []).join(", ");
  document.getElementById("p-languages").value = (parsed.languages || []).join(", ");

  (parsed.work_experience || []).forEach(addExperienceEntry);
  (parsed.education || []).forEach(addEducationEntry);
  (parsed.projects || []).forEach(addProjectEntry);

  if (!(parsed.work_experience || []).length) addExperienceEntry();
  if (!(parsed.education || []).length) addEducationEntry();
}

const saveError = document.getElementById("save-error");
const saveBtn = document.getElementById("save-btn");

document.getElementById("profile-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  saveError.classList.add("hidden");

  const parsedData = {
    personal_info: {
      name: document.getElementById("p-name").value.trim(),
      email: document.getElementById("p-email").value.trim(),
      phone: document.getElementById("p-phone").value.trim(),
      location: document.getElementById("p-location").value.trim(),
    },
    professional_summary: document.getElementById("p-summary").value.trim(),
    work_experience: collectExperience(),
    education: collectEducation(),
    skills: splitCommaList(document.getElementById("p-skills").value),
    languages: splitCommaList(document.getElementById("p-languages").value),
    projects: collectProjects(),
  };

  const pending = JSON.parse(sessionStorage.getItem("pendingProfile") || "{}");

  saveBtn.disabled = true;
  saveBtn.textContent = "שומר...";
  try {
    await saveCoreProfile(pending.storagePath, parsedData);
    sessionStorage.removeItem("pendingProfile");
    window.location.href = "/dashboard.html";
  } catch (err) {
    saveError.textContent = err.message || "השמירה נכשלה, נסו שוב";
    saveError.classList.remove("hidden");
    saveBtn.disabled = false;
    saveBtn.textContent = "שמירה והמשך";
  }
});

async function saveCoreProfile(storagePath, parsedData) {
  const userId = getCurrentUserId();
  const res = await supabaseFetch("/rest/v1/core_profiles?on_conflict=user_id", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates",
    },
    body: JSON.stringify({
      user_id: userId,
      original_resume_url: storagePath,
      parsed_data: parsedData,
    }),
  });
  if (!res.ok) throw new Error("שמירת הפרופיל נכשלה");
}

(async function init() {
  const hasSession = isAuthenticated() || (await restoreSession());
  if (!hasSession) {
    window.location.href = "/index.html";
    return;
  }

  const pending = JSON.parse(sessionStorage.getItem("pendingProfile") || "null");
  if (!pending) {
    window.location.href = "/index.html";
    return;
  }
  populateForm(pending.parsedData);
})();
