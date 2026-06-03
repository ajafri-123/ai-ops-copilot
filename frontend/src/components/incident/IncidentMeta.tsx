"use client";

import { clsx } from "clsx";
import {
  Activity,
  Calendar,
  Clock,
  Hash,
  Layers,
  RefreshCw,
  Server,
} from "lucide-react";
import type { Incident } from "@/lib/types";
import { SEVERITY_DOT, STATUS_BADGE, relativeTime } from "@/lib/severity";
import { SeverityBadge } from "@/components/SeverityBadge";

interface Props {
  incident: Incident;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function duration(a: string, b: string): string {
  const diff = Math.abs(new Date(b).getTime() - new Date(a).getTime()) / 1000;
  if (diff < 120) return `${Math.round(diff)}s`;
  if (diff < 3600) return `${Math.round(diff / 60)}m`;
  const h = Math.floor(diff / 3600);
  const m = Math.round((diff % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function IncidentMeta({ incident }: Props) {
  const alertCount = incident.events.filter(
    (e) => e.event_type === "alert_added",
  ).length;

  const rows = [
    {
      icon: <Hash className="h-3.5 w-3.5" />,
      label: "Incident ID",
      value: <span className="font-mono text-white">INC-{String(incident.id).padStart(4, "0")}</span>,
    },
    {
      icon: <Activity className="h-3.5 w-3.5" />,
      label: "Severity",
      value: <SeverityBadge severity={incident.severity} size="sm" pulse />,
    },
    {
      icon: <Server className="h-3.5 w-3.5" />,
      label: "Status",
      value: (
        <span
          className={clsx(
            "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
            STATUS_BADGE[incident.status] ?? "bg-slate-500/15 text-slate-400 border-slate-500/30",
          )}
        >
          {incident.status}
        </span>
      ),
    },
    {
      icon: <Layers className="h-3.5 w-3.5" />,
      label: "Services",
      value: (
        <span className="font-medium text-white">
          {incident.affected_services?.length ?? 0}
        </span>
      ),
    },
    {
      icon: <Activity className="h-3.5 w-3.5" />,
      label: "Alerts",
      value: <span className="font-medium text-white">{alertCount}</span>,
    },
    {
      icon: <Calendar className="h-3.5 w-3.5" />,
      label: "Opened",
      value: (
        <span className="text-white">
          {formatDate(incident.created_at)}
        </span>
      ),
    },
    {
      icon: <RefreshCw className="h-3.5 w-3.5" />,
      label: "Last updated",
      value: <span className="text-white">{relativeTime(incident.updated_at)}</span>,
    },
    {
      icon: <Clock className="h-3.5 w-3.5" />,
      label: "Duration",
      value: (
        <span className="font-medium text-white">
          {duration(incident.created_at, incident.updated_at)}
        </span>
      ),
    },
  ];

  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] overflow-hidden">
      <div className="border-b border-white/[0.07] px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Incident Details
        </h3>
      </div>
      <div className="divide-y divide-white/[0.04]">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex items-center justify-between gap-3 px-4 py-2.5"
          >
            <div className="flex items-center gap-2 text-xs text-slate-500">
              {row.icon}
              {row.label}
            </div>
            <div className="text-xs">{row.value}</div>
          </div>
        ))}
      </div>

      {/* Affected services */}
      {incident.affected_services && incident.affected_services.length > 0 && (
        <div className="border-t border-white/[0.07] p-4">
          <p className="mb-2.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Affected Services
          </p>
          <div className="flex flex-wrap gap-1.5">
            {incident.affected_services.map((svc) => (
              <span
                key={svc}
                className="flex items-center gap-1.5 rounded-md border border-white/[0.08] bg-white/[0.04] px-2.5 py-1 text-xs font-mono text-slate-300"
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
        </div>
      )}
    </div>
  );
}
