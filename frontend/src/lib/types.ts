// ─────────────────────────────────────────────
// Severity & Status enums (mirror backend)
// ─────────────────────────────────────────────

export type AlertSeverity = "critical" | "high" | "medium" | "low" | "info";
export type AlertStatus = "open" | "acknowledged" | "resolved" | "suppressed";

export type IncidentSeverity = "critical" | "high" | "medium" | "low";
export type IncidentStatus =
  | "open"
  | "investigating"
  | "identified"
  | "monitoring"
  | "resolved"
  | "closed";

export type EventType =
  | "alert_added"
  | "status_changed"
  | "comment"
  | "ai_analysis"
  | "remediation_applied"
  | "escalated"
  | "resolved";

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type Significance = "low" | "medium" | "high" | "critical";

// ─────────────────────────────────────────────
// Domain models
// ─────────────────────────────────────────────

export interface Alert {
  id: number;
  source: string;
  severity: AlertSeverity;
  title: string;
  description: string | null;
  service_name: string;
  environment: string;
  timestamp: string;
  status: AlertStatus;
  raw_payload: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentEvent {
  id: number;
  incident_id: number;
  alert_id: number | null;
  event_type: EventType;
  message: string;
  timestamp: string;
}

export interface Incident {
  id: number;
  title: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  affected_services: string[] | null;
  summary: string | null;
  root_cause: string | null;
  remediation_steps: string[] | null;
  created_at: string;
  updated_at: string;
  events: IncidentEvent[];
}

// ─────────────────────────────────────────────
// AI Analysis
// ─────────────────────────────────────────────

export interface TimelineEntry {
  timestamp: string;
  event: string;
  source: string;
  significance: Significance;
}

export interface RCAResult {
  summary: string;
  root_cause: string;
  timeline: TimelineEntry[];
  remediation_steps: string[];
  confidence: number;
  risk_level: RiskLevel;
  provider: string;
  model: string;
  analyzed_at: string;
}

export interface AnalyzeResponse {
  incident_id: number;
  analysis: RCAResult;
  alerts_analyzed: number;
  events_analyzed: number;
}

// ─────────────────────────────────────────────
// Service graph
// ─────────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  affected: boolean;
  group: "primary" | "dependency";
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
}

export interface ServiceGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ─────────────────────────────────────────────
// Integrations
// ─────────────────────────────────────────────

export type IntegrationProvider =
  | "aws_cloudwatch"
  | "datadog"
  | "sentry"
  | "github_actions"
  | "kubernetes"
  | "slack";

export type IntegrationStatus = "connected" | "disconnected" | "error";

export interface Integration {
  id: number;
  organization_id: number;
  provider: IntegrationProvider;
  name: string;
  status: IntegrationStatus;
  last_sync: string | null;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface TestAlertResponse {
  integration_id: number;
  provider: string;
  alert_id: number;
  alert_title: string;
  alert_severity: string;
  incident_id: number;
  incident_title: string;
  created_new_incident: boolean;
  correlation_score: number;
}

// ─────────────────────────────────────────────
// WebSocket event envelope
// ─────────────────────────────────────────────

export type WsEventType =
  | "connection.ack"
  | "snapshot"
  | "alert.created"
  | "alert.correlated"
  | "incident.created"
  | "incident.updated"
  | "incident.escalated";

export interface WsEnvelope<T = unknown> {
  event: WsEventType;
  timestamp: string;
  data: T;
}

export interface SnapshotData {
  alerts: Alert[];
  incidents: Incident[];
}

export interface AlertCorrelatedData {
  alert: Pick<Alert, "id" | "title" | "source" | "severity" | "service_name">;
  incident_id: number;
  incident_title: string;
  created_new_incident: boolean;
  reason: string;
}

export interface IncidentUpdatedData {
  incident: Incident;
  changed_fields: string[];
}

export interface IncidentEscalatedData {
  incident_id: number;
  old_severity: IncidentSeverity;
  new_severity: IncidentSeverity;
  triggered_by_alert_id: number | null;
}
