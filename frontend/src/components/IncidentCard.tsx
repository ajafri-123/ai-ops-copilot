"use client";

import { clsx } from "clsx";
import { ArrowUpRight, ChevronRight, Clock, Layers, Zap } from "lucide-react";
import Link from "next/link";
import type { Incident } from "@/lib/types";
import {
  SEVERITY_BORDER_LEFT,
  STATUS_BADGE,
  relativeTime,
} from "@/lib/severity";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  incident: Incident;
  selected?: boolean;
  onClick?: () => void;
}

export function IncidentCard({ incident, selected, onClick }: Props) {
  const alertCount = incident.events.filter(
    (e) => e.event_type === "alert_added",
  ).length;

  return (
    <div
      className={clsx(
        "group relative rounded-xl border border-l-[3px] p-4 transition-all",
        SEVERITY_BORDER_LEFT[incident.severity] ?? "border-l-slate-500",
        selected
          ? "border-indigo-500/40 bg-indigo-500/[0.07]"
          : "border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.05]",
      )}
    >
      {/* Main clickable area (opens side panel) */}
      <button
        onClick={onClick}
        className="w-full text-left focus:outline-none"
      >
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[10px] text-slate-600">
                INC-{String(incident.id).padStart(4, "0")}
              </span>
              <SeverityBadge severity={incident.severity} size="sm" pulse />
              <span
                className={clsx(
                  "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
                  STATUS_BADGE[incident.status] ??
                    "bg-slate-500/15 text-slate-400 border-slate-500/30",
                )}
              >
                {incident.status}
              </span>
            </div>
            <p className="mt-2 text-sm font-semibold leading-snug text-white line-clamp-2">
              {incident.title}
            </p>
          </div>
          <ChevronRight
            className={clsx(
              "mt-1 h-4 w-4 flex-shrink-0 text-slate-700 transition-transform",
              selected && "rotate-90 text-indigo-400",
            )}
          />
        </div>

        {/* Affected services */}
        {incident.affected_services && incident.affected_services.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {incident.affected_services.slice(0, 3).map((svc) => (
              <span
                key={svc}
                className="inline-flex items-center gap-1 rounded-md bg-white/[0.05] px-2 py-0.5 font-mono text-[10px] text-slate-400"
              >
                <Layers className="h-2.5 w-2.5" />
                {svc}
              </span>
            ))}
            {incident.affected_services.length > 3 && (
              <span className="rounded-md bg-white/[0.05] px-2 py-0.5 text-[10px] text-slate-500">
                +{incident.affected_services.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Footer stats */}
        <div className="mt-3 flex items-center gap-4 text-xs text-slate-600">
          <span className="flex items-center gap-1">
            <Zap className="h-3 w-3" />
            {alertCount} alert{alertCount !== 1 ? "s" : ""}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {relativeTime(incident.created_at)}
          </span>
        </div>
      </button>

      {/* "View full details" link — shown on hover */}
      <Link
        href={`/incidents/${incident.id}`}
        onClick={(e) => e.stopPropagation()}
        className={clsx(
          "absolute right-3 top-3 flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-medium text-slate-600 transition",
          "opacity-0 group-hover:opacity-100",
          "hover:bg-white/[0.08] hover:text-indigo-400",
        )}
        title="Open full detail page"
      >
        <ArrowUpRight className="h-3 w-3" />
        Details
      </Link>
    </div>
  );
}
