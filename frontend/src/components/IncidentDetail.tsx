"use client";

import { clsx } from "clsx";
import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clock,
  Cpu,
  GitBranch,
  Layers,
  Loader2,
  MessageSquare,
  ShieldAlert,
  Sparkles,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { analyzeIncident, patchIncident } from "@/lib/api";
import {
  SEVERITY_BADGE,
  SEVERITY_DOT,
  STATUS_BADGE,
  confidenceColor,
  confidenceLabel,
  relativeTime,
} from "@/lib/severity";
import type { Incident, IncidentEvent, RCAResult, TimelineEntry } from "@/lib/types";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  incident: Incident;
  onClose: () => void;
}

const EVENT_ICON: Record<string, React.ReactNode> = {
  alert_added: <Zap className="h-3.5 w-3.5 text-yellow-400" />,
  status_changed: <GitBranch className="h-3.5 w-3.5 text-blue-400" />,
  comment: <MessageSquare className="h-3.5 w-3.5 text-slate-400" />,
  ai_analysis: <Cpu className="h-3.5 w-3.5 text-indigo-400" />,
  remediation_applied: <Wrench className="h-3.5 w-3.5 text-green-400" />,
  escalated: <AlertTriangle className="h-3.5 w-3.5 text-red-400" />,
  resolved: <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />,
};

const SIGNIFICANCE_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-slate-500",
};

const INCIDENT_STATUSES = [
  "open",
  "investigating",
  "identified",
  "monitoring",
  "resolved",
  "closed",
] as const;

export function IncidentDetail({ incident, onClose }: Props) {
  const [showAllEvents, setShowAllEvents] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<RCAResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "ai" | "timeline">("overview");
  const [savingStatus, setSavingStatus] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  const visibleEvents = showAllEvents
    ? incident.events
    : incident.events.slice(0, 5);

  // Use live AI result if available, otherwise fall back to what's on the incident
  const rootCause = analysisResult?.root_cause ?? incident.root_cause;
  const remediationSteps = analysisResult?.remediation_steps ?? incident.remediation_steps;
  const summary = analysisResult?.summary ?? incident.summary;
  const hasAiData = !!(rootCause || remediationSteps?.length);

  const runAnalysis = async () => {
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const resp = await analyzeIncident(incident.id);
      setAnalysisResult(resp.analysis);
      setActiveTab("ai");
    } catch (e) {
      setAnalysisError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const changeStatus = async (next: string) => {
    if (next === incident.status) return;
    setSavingStatus(true);
    setStatusError(null);
    try {
      // The resulting incident.updated WS event refreshes dashboard state.
      await patchIncident(incident.id, { status: next });
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : "Failed to update status");
    } finally {
      setSavingStatus(false);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-cyan-500/[0.12] bg-[#06101f] shadow-glow-cyan">
      {/* ── Header ── */}
      <div className="flex flex-shrink-0 items-start justify-between gap-4 border-b border-cyan-500/[0.08] px-5 py-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-slate-500">#{incident.id}</span>
            <SeverityBadge severity={incident.severity} pulse />
            {/* Status control — acknowledge / resolve / close from the UI */}
            <select
              value={incident.status}
              onChange={(e) => changeStatus(e.target.value)}
              disabled={savingStatus}
              aria-label="Incident status"
              className={clsx(
                "cursor-pointer rounded-full border bg-transparent px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide outline-none transition focus:ring-1 focus:ring-cyan-500/40",
                savingStatus && "cursor-wait opacity-60",
                STATUS_BADGE[incident.status] ??
                  "bg-slate-500/15 text-slate-400 border-slate-500/30",
              )}
            >
              {INCIDENT_STATUSES.map((s) => (
                <option key={s} value={s} className="bg-[#06101f] text-slate-300">
                  {s}
                </option>
              ))}
            </select>
            {incident.status !== "resolved" && incident.status !== "closed" && (
              <button
                onClick={() => changeStatus("resolved")}
                disabled={savingStatus}
                className="inline-flex items-center gap-1 rounded-full border border-green-500/30 bg-green-500/10 px-2.5 py-0.5 text-xs font-medium text-green-400 transition hover:bg-green-500/20 disabled:opacity-50"
              >
                <CheckCircle2 className="h-3 w-3" />
                Resolve
              </button>
            )}
          </div>
          <h2 className="mt-2 text-sm font-semibold leading-snug text-white">
            {incident.title}
          </h2>
          {statusError && (
            <p className="mt-1.5 text-xs text-red-400" role="alert">{statusError}</p>
          )}
        </div>

        <div className="flex flex-shrink-0 items-center gap-2">
          {/* Analyze button */}
          <button
            onClick={runAnalysis}
            disabled={analyzing}
            className={clsx(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition",
              analyzing
                ? "cursor-not-allowed bg-indigo-500/20 text-indigo-400"
                : "bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200",
            )}
          >
            {analyzing ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Analyzing…
              </>
            ) : (
              <>
                <BrainCircuit className="h-3.5 w-3.5" />
                {hasAiData ? "Re-analyze" : "Analyze"}
              </>
            )}
          </button>

          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/10 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* ── Tab bar ── */}
      <div className="flex flex-shrink-0 items-center gap-0.5 border-b border-cyan-500/[0.08] px-5 pt-2">
        {(
          [
            { id: "overview", label: "Overview" },
            {
              id: "ai",
              label: "AI Analysis",
              badge: hasAiData,
              dot: true,
            },
            { id: "timeline", label: "Timeline", count: incident.events.length },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "relative flex items-center gap-1.5 px-3 pb-2 pt-1 text-xs font-medium transition",
              activeTab === tab.id
                ? "text-white after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:rounded-full after:bg-cyan-500"
                : "text-slate-500 hover:text-slate-300",
            )}
          >
            {tab.label}
            {"count" in tab && tab.count !== undefined && (
              <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] tabular-nums">
                {tab.count}
              </span>
            )}
            {"dot" in tab && tab.dot && hasAiData && (
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            )}
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {/* ── Overview tab ── */}
        {activeTab === "overview" && (
          <div className="space-y-5">
            {/* Affected services */}
            {incident.affected_services && incident.affected_services.length > 0 && (
              <Section
                title="Affected Services"
                icon={<Layers className="h-3.5 w-3.5" />}
              >
                <div className="flex flex-wrap gap-2">
                  {incident.affected_services.map((svc) => (
                    <span
                      key={svc}
                      className="flex items-center gap-1.5 rounded-md bg-white/[0.06] px-3 py-1.5 text-xs font-mono text-slate-300"
                    >
                      <span
                        className={clsx(
                          "h-1.5 w-1.5 rounded-full",
                          SEVERITY_DOT[incident.severity],
                        )}
                      />
                      {svc}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            {/* Summary */}
            {summary && (
              <Section title="Summary">
                <p className="text-sm leading-relaxed text-slate-400">{summary}</p>
              </Section>
            )}

            {/* Quick AI call-to-action if no data yet */}
            {!hasAiData && !analyzing && (
              <button
                onClick={runAnalysis}
                className="w-full rounded-xl border border-dashed border-cyan-500/20 bg-cyan-500/[0.04] px-4 py-5 text-center transition hover:border-cyan-500/30 hover:bg-cyan-500/[0.07]"
              >
                <BrainCircuit className="mx-auto mb-2 h-6 w-6 text-indigo-400" />
                <p className="text-sm font-medium text-cyan-300">
                  Run AI root-cause analysis
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Correlates all alerts and generates root cause, timeline, and remediation steps
                </p>
              </button>
            )}

            {analyzing && <AnalyzingState />}
          </div>
        )}

        {/* ── AI Analysis tab ── */}
        {activeTab === "ai" && (
          <div className="space-y-5">
            {analyzing && <AnalyzingState />}

            {analysisError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {analysisError}
              </div>
            )}

            {!analyzing && !analysisResult && !hasAiData && (
              <div className="flex flex-col items-center gap-3 py-8 text-center">
                <BrainCircuit className="h-10 w-10 text-slate-600" />
                <p className="text-sm text-slate-500">
                  No AI analysis yet. Click{" "}
                  <button
                    onClick={runAnalysis}
                    className="text-cyan-400 hover:underline"
                  >
                    Analyze
                  </button>{" "}
                  to generate one.
                </p>
              </div>
            )}

            {(analysisResult || hasAiData) && !analyzing && (
              <>
                {/* Confidence + provider badge */}
                {analysisResult && (
                  <ConfidenceCard result={analysisResult} />
                )}

                {/* Root cause */}
                {rootCause && (
                  <Section
                    title="Root Cause"
                    icon={<Cpu className="h-3.5 w-3.5 text-indigo-400" />}
                    accent="indigo"
                  >
                    <p className="text-sm leading-relaxed text-slate-300">
                      {rootCause}
                    </p>
                  </Section>
                )}

                {/* AI Timeline */}
                {analysisResult?.timeline && analysisResult.timeline.length > 0 && (
                  <Section
                    title="Reconstructed Timeline"
                    icon={<Clock className="h-3.5 w-3.5 text-blue-400" />}
                    accent="blue"
                  >
                    <AITimeline entries={analysisResult.timeline} />
                  </Section>
                )}

                {/* Remediation */}
                {remediationSteps && remediationSteps.length > 0 && (
                  <Section
                    title="Remediation Steps"
                    icon={<Wrench className="h-3.5 w-3.5 text-green-400" />}
                    accent="green"
                  >
                    <RemediationList steps={remediationSteps} />
                  </Section>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Timeline tab ── */}
        {activeTab === "timeline" && (
          <div className="space-y-1">
            {incident.events.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                No events recorded yet.
              </p>
            ) : (
              <>
                <div className="relative space-y-0">
                  <div className="absolute left-[7px] top-2 bottom-2 w-px bg-white/[0.06]" />
                  {visibleEvents.map((ev) => (
                    <EventRow key={ev.id} event={ev} />
                  ))}
                </div>
                {incident.events.length > 5 && (
                  <button
                    onClick={() => setShowAllEvents((p) => !p)}
                    className="mt-1 flex items-center gap-1 text-xs text-slate-500 transition hover:text-slate-300"
                  >
                    <ChevronDown
                      className={clsx(
                        "h-3.5 w-3.5 transition-transform",
                        showAllEvents && "rotate-180",
                      )}
                    />
                    {showAllEvents
                      ? "Show less"
                      : `Show ${incident.events.length - 5} more events`}
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────

function AnalyzingState() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-cyan-500/15 bg-cyan-500/[0.04] px-4 py-8 text-center">
      <div className="relative">
        <BrainCircuit className="h-8 w-8 text-indigo-400" />
        <span className="absolute -right-1 -top-1 flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-indigo-500" />
        </span>
      </div>
      <div>
        <p className="text-sm font-medium text-cyan-300">AI is analyzing…</p>
        <p className="mt-0.5 text-xs text-slate-500">
          Correlating alerts, building timeline, identifying root cause
        </p>
      </div>
      <div className="mt-1 flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-indigo-500 opacity-80"
            style={{ animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }}
          />
        ))}
      </div>
    </div>
  );
}

function ConfidenceCard({ result }: { result: RCAResult }) {
  const pct = Math.round(result.confidence * 100);
  const barColor = confidenceColor(result.confidence);
  const label = confidenceLabel(result.confidence);

  const riskBadge =
    SEVERITY_BADGE[result.risk_level as keyof typeof SEVERITY_BADGE] ??
    "bg-slate-500/15 text-slate-400 border-slate-500/30";

  const isMock = result.provider === "mock";

  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-4">
      {isMock && (
        <div
          role="note"
          className="mb-3 flex items-start gap-2 rounded-lg border border-amber-500/25 bg-amber-500/[0.08] px-3 py-2 text-[11px] leading-relaxed text-amber-300"
        >
          <ShieldAlert className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
          <span>
            <strong>Simulated analysis.</strong> No <code>OPENAI_API_KEY</code> is configured, so this
            root cause and remediation are produced by a pattern-matching mock — not a real LLM. Do not
            act on these steps in a live environment.
          </span>
        </div>
      )}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            AI Analysis
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase",
              riskBadge,
            )}
          >
            <ShieldAlert className="h-3 w-3" />
            {result.risk_level} risk
          </span>
          <span className="rounded-md bg-white/[0.06] px-2 py-0.5 text-[10px] text-slate-500 font-mono">
            {result.provider}/{result.model}
          </span>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">{label}</span>
          <span className="font-bold tabular-nums text-white">{pct}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className={clsx("h-full rounded-full transition-all duration-700", barColor)}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function AITimeline({ entries }: { entries: TimelineEntry[] }) {
  return (
    <div className="relative space-y-0">
      <div className="absolute left-[7px] top-2 bottom-2 w-px bg-white/[0.06]" />
      {entries.map((entry, i) => (
        <div key={i} className="relative flex gap-3 pb-3 pl-5">
          <span
            className={clsx(
              "absolute left-[3px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-[#06101f]",
              SIGNIFICANCE_DOT[entry.significance] ?? "bg-slate-500",
            )}
          />
          <div className="min-w-0 flex-1">
            <p className="text-xs leading-relaxed text-slate-300">{entry.event}</p>
            <div className="mt-0.5 flex gap-2 text-[10px] text-slate-600">
              <span className="font-mono">{entry.timestamp}</span>
              <span>·</span>
              <span className="uppercase">{entry.source}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function RemediationList({ steps }: { steps: string[] }) {
  const [checked, setChecked] = useState<Set<number>>(new Set());

  const toggle = (i: number) =>
    setChecked((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });

  return (
    <ol className="space-y-2">
      {steps.map((step, i) => {
        const done = checked.has(i);
        const text = step.replace(/^\d+\.\s*/, "");
        return (
          <li
            key={i}
            className={clsx(
              "flex cursor-pointer gap-3 rounded-lg border px-3 py-2.5 text-sm transition",
              done
                ? "border-green-500/20 bg-green-500/[0.06] text-slate-500 line-through"
                : "border-white/[0.06] bg-white/[0.03] text-slate-300 hover:border-white/10 hover:bg-white/[0.05]",
            )}
            onClick={() => toggle(i)}
          >
            <span
              className={clsx(
                "mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold transition",
                done
                  ? "bg-green-500/20 text-green-400"
                  : "bg-white/[0.08] text-slate-400",
              )}
            >
              {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : i + 1}
            </span>
            <span className="leading-relaxed">{text}</span>
          </li>
        );
      })}
    </ol>
  );
}

function Section({
  title,
  icon,
  accent,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  accent?: "indigo" | "green" | "blue";
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3
        className={clsx(
          "mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest",
          accent === "indigo" && "text-indigo-400",
          accent === "green" && "text-green-400",
          accent === "blue" && "text-blue-400",
          !accent && "text-slate-500",
        )}
      >
        {icon}
        {title}
      </h3>
      {children}
    </div>
  );
}

function EventRow({ event }: { event: IncidentEvent }) {
  return (
    <div className="relative flex gap-3 pb-4 pl-5">
      <span className="absolute left-0 top-1.5 flex h-3.5 w-3.5 items-center justify-center">
        {EVENT_ICON[event.event_type] ?? (
          <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-relaxed text-slate-300">{event.message}</p>
        <p className="mt-0.5 text-[10px] text-slate-600">
          {relativeTime(event.timestamp)}
        </p>
      </div>
    </div>
  );
}
