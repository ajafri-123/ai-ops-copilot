import type { Alert, AnalyzeResponse, Incident, Integration, ServiceGraphResponse, TestAlertResponse } from "./types";
import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_URL =
  (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000") + "/api/v1/ws";

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
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Login failed");
  }
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
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Signup failed");
  }
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

  const res = await fetch(`${API_BASE}/api/v1/alerts?${qs}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch alerts");
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

  const res = await fetch(`${API_BASE}/api/v1/incidents?${qs}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch incidents");
  return res.json();
}

export async function fetchIncident(id: number): Promise<Incident> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${id}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch incident ${id}`);
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
  const res = await fetch(`${API_BASE}/api/v1/incidents/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to update incident ${id}`);
  return res.json();
}

export async function fetchAlert(id: number): Promise<Alert> {
  const res = await fetch(`${API_BASE}/api/v1/alerts/${id}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch alert ${id}`);
  return res.json();
}

export async function fetchIncidentGraph(id: number): Promise<ServiceGraphResponse> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${id}/graph`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch graph for incident ${id}`);
  return res.json();
}

// ─────────────────────────────────────────────
// AI Analysis
// ─────────────────────────────────────────────

export async function analyzeIncident(id: number): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${id}/analyze`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Analysis failed for incident ${id}`);
  return res.json();
}

// ─────────────────────────────────────────────
// Integrations
// ─────────────────────────────────────────────

export async function fetchIntegrations(): Promise<Integration[]> {
  const res = await fetch(`${API_BASE}/api/v1/integrations`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch integrations");
  return res.json();
}

export async function createIntegration(provider: string, name?: string): Promise<Integration> {
  const res = await fetch(`${API_BASE}/api/v1/integrations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ provider, name }),
  });
  if (!res.ok) throw new Error("Failed to create integration");
  return res.json();
}

export async function patchIntegration(
  id: number,
  payload: { status?: string; name?: string; config?: Record<string, unknown> }
): Promise<Integration> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update integration");
  return res.json();
}

export async function sendTestAlert(id: number): Promise<TestAlertResponse> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/${id}/test-alert`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Test alert failed");
  }
  return res.json();
}

// ─────────────────────────────────────────────
// Demo
// ─────────────────────────────────────────────

export async function triggerDemoScenario(scenario: string) {
  const res = await fetch(`${API_BASE}/api/v1/alerts/demo-generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ scenario }),
  });
  if (!res.ok) throw new Error("Demo generation failed");
  return res.json();
}
