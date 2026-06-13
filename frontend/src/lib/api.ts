import type { Alert, AnalyzeResponse, Incident, Integration, ServiceGraphResponse, TestAlertResponse } from "./types";
import { clearAuth, getAuthHeaders } from "./auth";

// Server-side (SSR/RSC) uses INTERNAL_API_URL so Docker containers can
// reach the backend via its service name rather than localhost.
// Client-side always uses the public URL (already resolved in the browser).
const API_BASE =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");
export const WS_URL =
  (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000") + "/api/v1/ws";

// ─────────────────────────────────────────────
// Shared fetch helpers
// ─────────────────────────────────────────────

/**
 * Turn a FastAPI error body into a readable message.
 * `detail` can be a plain string or a Pydantic 422 array of
 * { loc, msg, type } objects — never show the user "[object Object]".
 */
export function parseApiError(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => {
        if (typeof d === "string") return d;
        const item = d as { msg?: string; loc?: unknown[] };
        const field = Array.isArray(item.loc) ? String(item.loc[item.loc.length - 1]) : "";
        return item.msg ? (field ? `${field}: ${item.msg}` : item.msg) : null;
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join("; ");
  }
  return fallback;
}

async function errorFromResponse(res: Response, fallback: string): Promise<Error> {
  const body = await res.json().catch(() => ({}));
  return new Error(parseApiError(body, fallback));
}

/**
 * Authenticated fetch wrapper. On 401 the session is over: clear local
 * auth state and send the user to the login page instead of letting every
 * widget fail with a generic "Failed to fetch…" error.
 */
async function authedFetch(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...(init?.headers ?? {}), ...getAuthHeaders() },
  });
  if (res.status === 401 && typeof window !== "undefined") {
    clearAuth();
    window.location.href = "/login?expired=1";
    throw new Error("Session expired — redirecting to login");
  }
  return res;
}

// ─────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  org_id: number;
  org_name: string;
  user_id: number;
  email: string;
}

export async function apiLogin(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw await errorFromResponse(res, "Login failed");
  return res.json();
}

export async function apiSignup(
  email: string,
  password: string,
  orgName: string,
  fullName?: string
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, org_name: orgName, full_name: fullName }),
  });
  if (!res.ok) throw await errorFromResponse(res, "Signup failed");
  return res.json();
}

// ─────────────────────────────────────────────
// Health
// ─────────────────────────────────────────────

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/v1/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json() as Promise<{
    status: string;
    version: string;
    services: Record<string, string>;
  }>;
}

// ─────────────────────────────────────────────
// Alerts
// ─────────────────────────────────────────────

export async function fetchAlerts(params?: {
  skip?: number;
  limit?: number;
  status?: string;
  source?: string;
  service_name?: string;
}): Promise<{ total: number; items: Alert[] }> {
  const qs = new URLSearchParams();
  if (params?.skip != null) qs.set("skip", String(params.skip));
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.status) qs.set("status", params.status);
  if (params?.source) qs.set("source", params.source);
  if (params?.service_name) qs.set("service_name", params.service_name);

  const res = await authedFetch(`/api/v1/alerts?${qs}`);
  if (!res.ok) throw await errorFromResponse(res, "Failed to fetch alerts");
  return res.json();
}

// ─────────────────────────────────────────────
// Incidents
// ─────────────────────────────────────────────

export async function fetchIncidents(params?: {
  skip?: number;
  limit?: number;
  status?: string;
}): Promise<{ total: number; items: Incident[] }> {
  const qs = new URLSearchParams();
  if (params?.skip != null) qs.set("skip", String(params.skip));
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.status) qs.set("status", params.status);

  const res = await authedFetch(`/api/v1/incidents?${qs}`);
  if (!res.ok) throw await errorFromResponse(res, "Failed to fetch incidents");
  return res.json();
}

export async function fetchIncident(id: number): Promise<Incident> {
  const res = await authedFetch(`/api/v1/incidents/${id}`);
  if (!res.ok) throw await errorFromResponse(res, `Failed to fetch incident ${id}`);
  return res.json();
}

export async function patchIncident(
  id: number,
  payload: Partial<{
    status: string;
    severity: string;
    root_cause: string;
    remediation_steps: string[];
    summary: string;
  }>
): Promise<Incident> {
  const res = await authedFetch(`/api/v1/incidents/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await errorFromResponse(res, `Failed to update incident ${id}`);
  return res.json();
}

export async function fetchAlert(id: number): Promise<Alert> {
  const res = await authedFetch(`/api/v1/alerts/${id}`);
  if (!res.ok) throw await errorFromResponse(res, `Failed to fetch alert ${id}`);
  return res.json();
}

export async function fetchIncidentGraph(id: number): Promise<ServiceGraphResponse> {
  const res = await authedFetch(`/api/v1/incidents/${id}/graph`);
  if (!res.ok) throw await errorFromResponse(res, `Failed to fetch graph for incident ${id}`);
  return res.json();
}

// ─────────────────────────────────────────────
// AI Analysis
// ─────────────────────────────────────────────

export async function analyzeIncident(id: number): Promise<AnalyzeResponse> {
  const res = await authedFetch(`/api/v1/incidents/${id}/analyze`, { method: "POST" });
  if (!res.ok) throw await errorFromResponse(res, `Analysis failed for incident ${id}`);
  return res.json();
}

// ─────────────────────────────────────────────
// Integrations
// ─────────────────────────────────────────────

export async function fetchIntegrations(): Promise<Integration[]> {
  const res = await authedFetch(`/api/v1/integrations`);
  if (!res.ok) throw await errorFromResponse(res, "Failed to fetch integrations");
  return res.json();
}

export async function createIntegration(provider: string, name?: string): Promise<Integration> {
  const res = await authedFetch(`/api/v1/integrations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, name }),
  });
  if (!res.ok) throw await errorFromResponse(res, "Failed to create integration");
  return res.json();
}

export async function patchIntegration(
  id: number,
  payload: { status?: string; name?: string; config?: Record<string, unknown> }
): Promise<Integration> {
  const res = await authedFetch(`/api/v1/integrations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await errorFromResponse(res, "Failed to update integration");
  return res.json();
}

export async function sendTestAlert(id: number): Promise<TestAlertResponse> {
  const res = await authedFetch(`/api/v1/integrations/${id}/test-alert`, {
    method: "POST",
  });
  if (!res.ok) throw await errorFromResponse(res, "Test alert failed");
  return res.json();
}

// ─────────────────────────────────────────────
// Demo
// ─────────────────────────────────────────────

export async function triggerDemoScenario(scenario: string) {
  const res = await authedFetch(`/api/v1/alerts/demo-generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!res.ok) throw await errorFromResponse(res, "Demo generation failed");
  return res.json();
}
