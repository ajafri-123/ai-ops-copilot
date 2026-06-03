"use client";

import { clsx } from "clsx";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  GitBranch,
  MessageSquare,
  Search,
  Wrench,
  Zap,
} from "lucide-react";
import { useState } from "react";
import type { IncidentEvent } from "@/lib/types";
import { SOURCE_COLOR, SOURCE_LABEL, relativeTime } from "@/lib/severity";

interface Props {
  events: IncidentEvent[];
  onAlertClick?: (alertId: number) => void;
}

type Filter = "all" | "alert_added" | "ai_analysis" | "status_changed" | "escalated";

const TYPE_META: Record<
  string,
  {
    label: string;
    icon: React.ReactNode;
    dotColor: string;
    lineColor: string;
    bg: string;
  }
> = {
  alert_added: {
    label: "Alert",
    icon: <Zap className="h-3.5 w-3.5 text-yellow-400" />,
    dotColor: "bg-yellow-500",
    lineColor: "border-yellow-500/30",
    bg: "bg-yellow-500/[0.04] border-yellow-500/10",
  },
  status_changed: {
    label: "Status",
    icon: <GitBranch className="h-3.5 w-3.5 text-blue-400" />,
    dotColor: "bg-blue-500",
    lineColor: "border-blue-500/30",
    bg: "bg-blue-500/[0.04] border-blue-500/10",
  },
  comment: {
    label: "Comment",
    icon: <MessageSquare className="h-3.5 w-3.5 text-slate-400" />,
    dotColor: "bg-slate-500",
    lineColor: "border-slate-500/20",
    bg: "bg-white/[0.02] border-white/[0.06]",
  },
  ai_analysis: {
    label: "AI",
    icon: <Bot className="h-3.5 w-3.5 text-indigo-400" />,
    dotColor: "bg-indigo-500",
    lineColor: "border-indigo-500/30",
    bg: "bg-indigo-500/[0.06] border-indigo-500/20",
  },
  remediation_applied: {
    label: "Remediation",
    icon: <Wrench className="h-3.5 w-3.5 text-green-400" />,
    dotColor: "bg-green-500",
    lineColor: "border-green-500/30",
    bg: "bg-green-500/[0.04] border-green-500/10",
  },
  escalated: {
    label: "Escalated",
    icon: <AlertTriangle className="h-3.5 w-3.5 text-red-400" />,
    dotColor: "bg-red-500",
    lineColor: "border-red-500/30",
    bg: "bg-red-500/[0.06] border-red-500/20",
  },
  resolved: {
    label: "Resolved",
    icon: <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />,
    dotColor: "bg-green-500",
    lineColor: "border-green-500/30",
    bg: "bg-green-500/[0.06] border-green-500/20",
  },
};

const FALLBACK_META = {
  label: "Event",
  icon: <span className="h-2 w-2 rounded-full bg-slate-500" />,
  dotColor: "bg-slate-500",
  lineColor: "border-slate-500/20",
  bg: "bg-white/[0.02] border-white/[0.06]",
};

const FILTER_OPTS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "alert_added", label: "Alerts" },
  { id: "ai_analysis", label: "AI" },
  { id: "status_changed", label: "Status" },
  { id: "escalated", label: "Escalations" },
];

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function IncidentTimeline({ events, onAlertClick }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");

  const sorted = [...events].sort((a, b) => {
    const ta = new Date(a.timestamp).getTime();
    const tb = new Date(b.timestamp).getTime();
    // Guard against malformed timestamps (NaN) — keep original order
    if (isNaN(ta) || isNaN(tb)) return 0;
    return ta - tb;
  });

  const filtered = sorted.filter((e) => {
    if (filter !== "all" && e.event_type !== filter) return false;
    if (search && !e.message.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  // Group by date
  const groups = new Map<string, IncidentEvent[]>();
  filtered.forEach((ev) => {
    const day = formatDate(ev.timestamp);
    if (!groups.has(day)) groups.set(day, []);
    groups.get(day)!.push(ev);
  });

  return (
    <div className="flex h-full flex-col gap-3">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Filter pills */}
        <div className="flex items-center gap-0.5 rounded-lg bg-white/[0.05] p-0.5">
          {FILTER_OPTS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setFilter(opt.id)}
              className={clsx(
                "rounded-md px-3 py-1 text-xs font-medium transition",
                filter === opt.id
                  ? "bg-white/10 text-white"
                  : "text-slate-500 hover:text-slate-300",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search events…"
            className="w-full rounded-lg border border-white/[0.07] bg-white/[0.04] pl-8 pr-3 py-1.5 text-xs text-slate-300 placeholder-slate-600 outline-none focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20"
          />
        </div>

        <span className="text-xs text-slate-600">{filtered.length} events</span>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto pr-1">
        {filtered.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-slate-600">
            No matching events
          </div>
        ) : (
          <div className="space-y-4">
            {[...groups.entries()].map(([day, dayEvents]) => (
              <div key={day}>
                {/* Date separator */}
                <div className="mb-3 flex items-center gap-3">
                  <div className="h-px flex-1 bg-white/[0.06]" />
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                    {day}
                  </span>
                  <div className="h-px flex-1 bg-white/[0.06]" />
                </div>

                <div className="relative space-y-2">
                  {/* Vertical timeline track */}
                  <div className="absolute left-[15px] top-3 bottom-3 w-px bg-white/[0.06]" />

                  {dayEvents.map((ev) => {
                    const meta = TYPE_META[ev.event_type] ?? FALLBACK_META;
                    const isAlert = ev.event_type === "alert_added" && ev.alert_id != null;

                    return (
                      <div key={ev.id} className="relative flex gap-3 pl-8">
                        {/* Dot */}
                        <span
                          className={clsx(
                            "absolute left-[9px] top-3.5 h-[13px] w-[13px] rounded-full border-2 border-[#0a0a15]",
                            meta.dotColor,
                          )}
                        />

                        {/* Card */}
                        <div
                          className={clsx(
                            "flex-1 rounded-lg border px-3 py-2.5 transition",
                            meta.bg,
                            isAlert &&
                              "cursor-pointer hover:brightness-110",
                          )}
                          onClick={
                            isAlert && ev.alert_id
                              ? () => onAlertClick?.(ev.alert_id!)
                              : undefined
                          }
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-1.5">
                              {meta.icon}
                              <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                                {meta.label}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-[10px] text-slate-600">
                              <span className="font-mono">{formatTime(ev.timestamp)}</span>
                              <span>{relativeTime(ev.timestamp)}</span>
                            </div>
                          </div>
                          <p className="mt-1.5 text-xs leading-relaxed text-slate-300">
                            {ev.message}
                          </p>
                          {isAlert && (
                            <p className="mt-1 text-[10px] text-indigo-400/70">
                              Click to view raw alert →
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
