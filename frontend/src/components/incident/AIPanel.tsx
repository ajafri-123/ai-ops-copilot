"use client";

import { clsx } from "clsx";
import {
  BrainCircuit,
  CheckCircle2,
  Clock,
  Cpu,
  Loader2,
  ShieldAlert,
  Sparkles,
  Wrench,
} from "lucide-react";
import { useState } from "react";
import { analyzeIncident } from "@/lib/api";
import {
  SEVERITY_BADGE,
  SEVERITY_DOT,
  confidenceColor,
  confidenceLabel,
} from "@/lib/severity";
import type { Incident, RCAResult, TimelineEntry } from "@/lib/types";

interface Props {
  incident: Incident;
  onAnalyzed?: (result: RCAResult) => void;
}

const SIGNIFICANCE_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-slate-500",
};

export function AIPanel({ incident, onAnalyzed }: Props) {
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<RCAResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rootCause = result?.root_cause ?? incident.root_cause;
  const remediationSteps = result?.remediation_steps ?? incident.remediation_steps;
  const hasData = !!(rootCause || remediationSteps?.length);

  const run = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const resp = await analyzeIncident(incident.id);
      setResult(resp.analysis);
      onAnalyzed?.(resp.analysis);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-5">
      {/* CTA or Re-analyze */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-white">AI Root-Cause Analysis</h3>
        </div>
        <button
          onClick={run}
          disabled={analyzing}
          className={clsx(
            "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition",
            analyzing
              ? "cursor-not-allowed bg-indigo-500/20 text-indigo-400"
              : "bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20",
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
              {hasData ? "Re-analyze" : "Run Analysis"}
            </>
          )}
        </button>
      </div>

      {/* Analyzing skeleton */}
      {analyzing && <AnalyzingState />}

      {/* Error */}
      {error && !analyzing && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!hasData && !analyzing && (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-white/10 py-16 text-center">
          <BrainCircuit className="h-10 w-10 text-slate-700" />
          <p className="text-sm font-medium text-slate-500">No analysis yet</p>
          <p className="max-w-xs text-xs text-slate-600">
            Click "Run Analysis" to correlate all alerts, build a causal timeline,
            and get actionable remediation steps.
          </p>
        </div>
      )}

      {/* Results */}
      {hasData && !analyzing && (
        <div className="flex flex-col gap-5 overflow-y-auto pb-2">
          {/* Confidence card */}
          {result && (
            <ConfidenceCard result={result} />
          )}

          {/* Root cause */}
          {rootCause && (
            <Section
              title="Root Cause"
              icon={<Cpu className="h-3.5 w-3.5 text-indigo-400" />}
              accent="indigo"
            >
              <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/[0.05] px-4 py-3">
                <p className="text-sm leading-relaxed text-slate-200">{rootCause}</p>
              </div>
            </Section>
          )}

          {/* AI Timeline */}
          {result?.timeline && result.timeline.length > 0 && (
            <Section
              title="Reconstructed Timeline"
              icon={<Clock className="h-3.5 w-3.5 text-blue-400" />}
              accent="blue"
            >
              <AITimeline entries={result.timeline} />
            </Section>
          )}

          {/* Remediation */}
          {remediationSteps && remediationSteps.length > 0 && (
            <Section
              title="Remediation Checklist"
              icon={<Wrench className="h-3.5 w-3.5 text-green-400" />}
              accent="green"
            >
              <RemediationChecklist steps={remediationSteps} />
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────

function AnalyzingState() {
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-indigo-500/20 bg-indigo-500/[0.04] px-6 py-10 text-center">
      <div className="relative">
        <div className="absolute inset-0 rounded-full bg-indigo-500/20 blur-xl" />
        <BrainCircuit className="relative h-9 w-9 text-indigo-400" />
        <span className="absolute -right-0.5 -top-0.5 flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-indigo-500" />
        </span>
      </div>
      <div>
        <p className="text-sm font-semibold text-indigo-300">Analyzing incident…</p>
        <p className="mt-1 text-xs text-slate-500">
          Correlating {" "}alerts · building timeline · identifying root cause
        </p>
      </div>
      <div className="flex gap-1.5">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-1.5 w-8 rounded-full bg-indigo-500/30 overflow-hidden"
          >
            <div
              className="h-full rounded-full bg-indigo-500"
              style={{
                animation: `pulse 1.5s ease-in-out ${i * 0.3}s infinite`,
                width: "60%",
              }}
            />
          </div>
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

  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
          <span className="text-xs font-semibold text-white">Analysis Result</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={clsx(
              "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide",
              riskBadge,
            )}
          >
            <ShieldAlert className="h-3 w-3" />
            {result.risk_level} risk
          </span>
          <span className="rounded-md bg-white/[0.05] px-2 py-0.5 font-mono text-[10px] text-slate-500">
            {result.provider} · {result.model}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400">{label}</span>
          <span className="text-sm font-bold tabular-nums text-white">{pct}%</span>
        </div>
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-white/[0.08]">
          <div
            className={clsx("h-full rounded-full transition-all duration-1000", barColor)}
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
      <div className="absolute left-[7px] top-2 bottom-0 w-px bg-white/[0.06]" />
      {entries.map((entry, i) => (
        <div key={i} className="relative flex gap-3 pb-3 pl-6">
          <span
            className={clsx(
              "absolute left-[3px] top-1.5 h-3 w-3 rounded-full border-2 border-[#0a0a15]",
              SIGNIFICANCE_DOT[entry.significance] ?? "bg-slate-500",
            )}
          />
          <div className="min-w-0 flex-1 rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-2">
            <p className="text-xs leading-relaxed text-slate-200">{entry.event}</p>
            <div className="mt-1 flex gap-2 text-[10px] text-slate-600">
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

function RemediationChecklist({ steps }: { steps: string[] }) {
  const [checked, setChecked] = useState<Set<number>>(new Set());

  const toggle = (i: number) =>
    setChecked((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });

  const doneCount = checked.size;

  return (
    <div>
      {/* Progress */}
      <div className="mb-3 flex items-center justify-between text-xs">
        <span className="text-slate-500">
          {doneCount}/{steps.length} completed
        </span>
        {doneCount === steps.length && steps.length > 0 && (
          <span className="text-green-400 flex items-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" />
            All done!
          </span>
        )}
      </div>
      <div className="mb-3 h-1 w-full overflow-hidden rounded-full bg-white/[0.08]">
        <div
          className="h-full rounded-full bg-green-500 transition-all duration-500"
          style={{ width: `${steps.length > 0 ? (doneCount / steps.length) * 100 : 0}%` }}
        />
      </div>

      <ol className="space-y-2">
        {steps.map((step, i) => {
          const done = checked.has(i);
          const text = step.replace(/^\d+\.\s*/, "");
          // Detect code-like lines (kubectl, aws, curl, etc.)
          const isCode = /^(kubectl|aws|curl|docker|helm|git|npm|yarn|pip|python|bash|sh)\s/.test(text.trim());

          return (
            <li
              key={i}
              onClick={() => toggle(i)}
              className={clsx(
                "group flex cursor-pointer gap-3 rounded-xl border p-3 transition-all",
                done
                  ? "border-green-500/20 bg-green-500/[0.05] opacity-60"
                  : "border-white/[0.07] bg-white/[0.03] hover:border-white/[0.12] hover:bg-white/[0.05]",
              )}
            >
              {/* Checkbox */}
              <div
                className={clsx(
                  "mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border transition-all",
                  done
                    ? "border-green-500/50 bg-green-500/20"
                    : "border-white/20 group-hover:border-white/40",
                )}
              >
                {done ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
                ) : (
                  <span className="text-[10px] font-bold text-slate-500">{i + 1}</span>
                )}
              </div>

              <div className="min-w-0 flex-1">
                {isCode ? (
                  <code
                    className={clsx(
                      "block rounded-md bg-black/30 px-3 py-2 font-mono text-[11px] leading-relaxed text-emerald-300",
                      done && "line-through opacity-50",
                    )}
                  >
                    {text}
                  </code>
                ) : (
                  <span
                    className={clsx(
                      "text-sm leading-relaxed text-slate-300",
                      done && "line-through text-slate-600",
                    )}
                  >
                    {text}
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
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
      <h4
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
      </h4>
      {children}
    </div>
  );
}
