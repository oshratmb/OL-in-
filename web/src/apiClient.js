import { decodeJwtPayload } from "./jwt.js";

const AI_SERVICE_URL = import.meta.env.VITE_AI_SERVICE_URL;
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

let accessToken = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function isAuthenticated() {
  return !!accessToken;
}

export function getCurrentUserId() {
  return accessToken ? decodeJwtPayload(accessToken).sub : null;
}

// The refresh token lives in an HttpOnly cookie the browser sends automatically;
// this just asks ai-service to mint a fresh access token from it.
export async function restoreSession() {
  const res = await fetch(`${AI_SERVICE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    accessToken = null;
    return false;
  }
  const data = await res.json();
  accessToken = data.access_token;
  return true;
}

// Calls our own ai-service (auth-proxied endpoints), retrying once after a
// silent refresh if the access token expired.
export async function aiServiceFetch(path, options = {}) {
  const doFetch = () =>
    fetch(`${AI_SERVICE_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        ...(options.headers || {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });

  let res = await doFetch();
  if (res.status === 401 && (await restoreSession())) {
    res = await doFetch();
  }
  return res;
}

// Used after any successful login/session-restore to route a returning user
// straight to their dashboard instead of back through onboarding.
export async function hasCompletedOnboarding() {
  const res = await supabaseFetch("/rest/v1/core_profiles?select=id&limit=1");
  if (!res.ok) return false;
  const rows = await res.json();
  return rows.length > 0;
}

// Direct calls to Supabase's own REST/Storage APIs — RLS enforces per-user
// access, so these don't need to go through ai-service at all.
export async function supabaseFetch(path, options = {}) {
  const doFetch = () =>
    fetch(`${SUPABASE_URL}${path}`, {
      ...options,
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${accessToken}`,
        ...(options.headers || {}),
      },
    });

  let res = await doFetch();
  if (res.status === 401 && (await restoreSession())) {
    res = await doFetch();
  }
  return res;
}
