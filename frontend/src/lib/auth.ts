const TOKEN_KEY = "aiops_token";
const USER_KEY = "aiops_user";

export interface AuthUser {
  user_id: number;
  email: string;
  org_id: number;
  org_name: string;
}

/** Read the `exp` (seconds since epoch) claim from a JWT without verifying it. */
function tokenExpiry(token: string): number | null {
  try {
    const [, payload] = token.split(".");
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp === "number" ? json.exp : null;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuth(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  // Mirror the token's expiry in a cookie so middleware can reject expired
  // sessions server-side (instead of trusting a cosmetic "logged in" flag).
  // Cookie lifetime is aligned to the token's own exp.
  const exp = tokenExpiry(token);
  const now = Math.floor(Date.now() / 1000);
  const maxAge = exp ? Math.max(0, exp - now) : 60 * 60 * 24 * 7;
  document.cookie = `aiops_exp=${exp ?? ""}; path=/; max-age=${maxAge}; SameSite=Lax`;
}

export function clearAuthCookie(): void {
  document.cookie = "aiops_exp=; path=/; max-age=0";
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  clearAuthCookie();
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}
