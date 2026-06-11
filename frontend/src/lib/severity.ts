import type { AlertSeverity, IncidentSeverity, IncidentStatus } from "./types";

// ─────────────────────────────────────────────
// Severity colour maps
// ─────────────────────────────────────────────

export const SEVERITY_BADGE: Record<AlertSeverity | IncidentSeverity, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/30 ring-red-500/20",
  high:     "bg-orange-500/15 text-orange-400 border-orange-500/30 ring-orange-500/20",
  medium:   "bg-amber-500/15 text-amber-400 border-amber-500/30 ring-amber-500/20",
  low:      "bg-blue-500/15 text-blue-400 border-blue-500/30 ring-blue-500/20",
  info:     "bg-slate-500/15 text-slate-400 border-slate-500/30 ring-slate-500/20",
};

export const SEVERITY_DOT: Record<AlertSeverity | IncidentSeverity, string> = {
  critical: "bg-red-500",
  high:     "bg-orange-500",
  medium:   "bg-amber-500",
  low:      "bg-blue-500",
  info:     "bg-slate-500",
};

export const SEVERITY_BORDER_LEFT: Record<AlertSeverity | IncidentSeverity, string> = {
  critical: "border-l-red-500",
  high:     "border-l-orange-500",
  medium:   "border-l-amber-500",
  low:      "border-l-blue-500",
  info:     "border-l-slate-600",
};

// ─────────────────────────────────────────────
// Incident status colour maps
// ─────────────────────────────────────────────

export const STATUS_BADGE: Record<IncidentStatus, string> = {
  open:          "bg-red-500/15 text-red-400 border-red-500/30",
  investigating: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  identified:    "bg-amber-500/15 text-amber-400 border-amber-500/30",
  monitoring:    "bg-blue-500/15 text-blue-400 border-blue-500/30",
  resolved:      "bg-green-500/15 text-green-400 border-green-500/30",
  closed:        "bg-slate-500/15 text-slate-400 border-slate-500/30",
};

// ─────────────────────────────────────────────
// Source icons (text fallback)
// ─────────────────────────────────────────────

export const SOURCE_LABEL: Record<string, string> = {
  aws:            "AWS",
  datadog:        "DD",
  sentry:         "SN",
  kubernetes:     "K8S",
  github_actions: "GH",
  pagerduty:      "PD",
};

export const SOURCE_COLOR: Record<string, string> = {
  aws:            "bg-orange-500/15 text-orange-300",
  datadog:        "bg-purple-500/15 text-purple-300",
  sentry:         "bg-indigo-500/15 text-indigo-300",
  kubernetes:     "bg-cyan-500/15 text-cyan-300",
  github_actions: "bg-slate-500/15 text-slate-300",
  pagerduty:      "bg-green-500/15 text-green-300",
};

// ─────────────────────────────────────────────
// Confidence bar colour
// ─────────────────────────────────────────────

export function confidenceColor(score: number): string {
  if (score >= 0.85) return "bg-green-500";
  if (score >= 0.65) return "bg-amber-500";
  if (score >= 0.4)  return "bg-orange-500";
  return "bg-red-500";
}

export function confidenceLabel(score: number): string {
  if (score >= 0.85) return "High confidence";
  if (score >= 0.65) return "Moderate confidence";
  if (score >= 0.4)  return "Low confidence";
  return "Speculative";
}

// ─────────────────────────────────────────────
// Relative time helper
// ─────────────────────────────────────────────

export function relativeTime(iso: string): string {
  if (typeof window === "undefined") return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)    return `${Math.round(diff)}s ago`;
  if (diff < 3600)  return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}
