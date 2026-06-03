const TOKEN_KEY = "aiops_token";
const ORG_KEY = "aiops_org";
const USER_KEY = "aiops_user";

export interface AuthUser {
  user_id: number;
  email: string;
  org_id: number;
  org_name: string;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuth(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  // Mirror presence in a cookie so the middleware can check it server-side.
  document.cookie = `aiops_auth=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

export function clearAuthCookie(): void {
  document.cookie = "aiops_auth=; path=/; max-age=0";
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(ORG_KEY);
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
