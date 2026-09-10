// Decodes a JWT payload client-side. No verification here — this is only
// used to read our own already-trusted access token's "sub" (user id);
// the real verification happens server-side (ai-service / Supabase RLS).
export function decodeJwtPayload(token) {
  const payload = token.split(".")[1];
  const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
  const json = decodeURIComponent(
    atob(base64)
      .split("")
      .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
      .join("")
  );
  return JSON.parse(json);
}
