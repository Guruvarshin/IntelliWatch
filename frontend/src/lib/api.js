import { cookies } from "next/headers";

/**
 * The NextAuth session cookie *is* the JWT the backend expects: auth.config.js
 * signs it with HS256 + AUTH_SECRET and sets `sub` to the user id (decision
 * 9/0.5). So we don't need a separate token-issuing step -- just forward the
 * raw cookie value as the bearer token.
 */
function getSessionToken() {
  const store = cookies();
  return (
    store.get("authjs.session-token")?.value ??
    store.get("__Secure-authjs.session-token")?.value
  );
}

export async function apiFetch(path, options = {}) {
  const token = getSessionToken();

  const res = await fetch(`${process.env.BACKEND_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Backend request failed (${res.status}): ${body}`);
  }

  if (res.status === 204) return null;
  return res.json();
}
