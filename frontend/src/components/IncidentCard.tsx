"use client";

import { clsx } from "clsx";
import { ArrowUpRight, Clock, Layers, Zap } from "lucide-react";
import Link from "next/link";
import type { Incident } from "@/lib/types";
import { STATUS_BADGE, relativeTime } from "@/lib/severity";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  incident: Incident;
  selected?: boolean;
  onClick?: () => void;
}

const SEVERITY_LEFT: Record<string, string> = {
  critical: "border-l-red-500",
  high:     "border-l-orange-500",
  medium:   "border-l-amber-500",
  low:      "border-l-blue-400",
  info:     "border-l-slate-600",
};

const SEVERITY_GLOW: Record<string, string> = {
  critical: "shadow-glow-red",
  high:     "shadow-glow-orange",
  medium:   "",
  low:      "",
  info:     "",
};

export function IncidentCard({ incident, selected, onClick }: Props) {
  const alertCount = incident.events.filter((e) => e.event_type === "alert_added").length;

  return (
    <div
      className={clsx(
        "group relative rounded-xl border border-l-[3px] bg-[#081320] p-3.5 transition-all",
        SEVERITY_LEFT[incident.severity] ?? "border-l-slate-600",
        selected
          ? "border-cyan-500/30 bg-[#0a1828] shadow-glow-cyan"
          : [
              "border-cyan-500/[0.07] hover:border-cyan-500/[0.14] hover:bg-[#0c1828]",
              incident.severity === "critical" && "hover:shadow-glow-red",
              incident.severity === "high"     && "hover:shadow-glow-orange",
            ],
      )}
    >
      <button onClick={onClick} className="w-full text-left focus:outline-none">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-mono text-[9px] text-slate-700">
                INC-{String(incident.id).padStart(4, "0")}
              </span>
              <SeverityBadge severity={incident.severity} size="sm" pulse />
              <span
                className={clsx(
                  "inline-flex items-center rounded-full border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide",
                  STATUS_BADGE[incident.status] ?? "bg-slate-500/15 text-slate-400 border-slate-500/30",
                )}
              >
                {incident.status}
              </span>
            </div>
            <p className="mt-2 text-xs font-semibold leading-snug text-slate-200 line-clamp-2 group-hover:text-white">
              {incident.title}
            </p>
          </div>
        </div>

        {/* Affected services */}
        {incident.affected_services && incident.affected_services.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1">
            {incident.affected_services.slice(0, 3).map((svc) => (
              <span
                key={svc}
                className="inline-flex items-center gap-1 rounded-md border border-cyan-500/[0.08] bg-cyan-500/[0.04] px-1.5 py-0.5 font-mono text-[9px] text-slate-500"
              >
                <Layers className="h-2.5 w-2.5 text-cyan-600" />
                {svc}
              </span>
            ))}
            {incident.affected_services.length > 3 && (
              <span className="rounded-md border border-cyan-500/[0.06] px-1.5 py-0.5 text-[9px] text-slate-600">
                +{incident.affected_services.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="mt-2.5 flex items-center gap-3 text-[10px] text-slate-700">
          <span className="flex items-center gap-1">
            <Zap className="h-3 w-3 text-slate-700" />
            {alertCount} alert{alertCount !== 1 ? "s" : ""}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3 text-slate-700" />
            {relativeTime(incident.created_at)}
          </span>
        </div>
      </button>

      {/* Full details link */}
      <Link
        href={`/incidents/${incident.id}`}
        onClick={(e) => e.stopPropagation()}
        className={clsx(
          "absolute right-2.5 top-2.5 flex items-center gap-1 rounded px-1.5 py-1 text-[9px] font-medium text-slate-700 transition",
          "opacity-0 group-hover:opacity-100",
          "hover:bg-cyan-500/10 hover:text-cyan-400",
        )}
        title="Open full detail page"
      >
        <ArrowUpRight className="h-3 w-3" />
        Details
      </Link>
    </div>
  );
}
