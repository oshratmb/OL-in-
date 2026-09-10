import { aiServiceFetch, setAccessToken } from "./apiClient.js";

export function validatePassword(password) {
  const problems = [];
  if (password.length < 8) problems.push("לפחות 8 תווים");
  if (!/[a-z]/.test(password)) problems.push("אות קטנה");
  if (!/[A-Z]/.test(password)) problems.push("אות גדולה");
  if (!/[0-9]/.test(password)) problems.push("ספרה");
  if (!/[^A-Za-z0-9]/.test(password)) problems.push("תו מיוחד");
  return problems;
}

async function handleAuthResponse(res) {
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "משהו השתבש");
  setAccessToken(data.access_token);
  return data.user;
}

export async function signUp(email, password, name) {
  const res = await aiServiceFetch("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  return handleAuthResponse(res);
}

// Returns { status: "ok", user } for a normal login, or
// { status: "mfa_enrollment_required" | "mfa_challenge_required", ... } for
// a Super Admin whose session isn't at aal2 yet (see mfa.js). Regular/Support
// users never see the mfa_* branches.
export async function logIn(email, password) {
  const res = await aiServiceFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "משהו השתבש");

  if (data.mfa_enrollment_required || data.mfa_challenge_required) {
    return {
      status: data.mfa_enrollment_required ? "mfa_enrollment_required" : "mfa_challenge_required",
      tempAccessToken: data.temp_access_token,
      factorId: data.factor_id,
    };
  }

  setAccessToken(data.access_token);
  return { status: "ok", user: data.user };
}

export async function logOut() {
  await aiServiceFetch("/auth/logout", { method: "POST" });
  setAccessToken(null);
}

export function startGoogleLogin() {
  window.location.href = `${import.meta.env.VITE_AI_SERVICE_URL}/auth/google/start`;
}
