"use client";

import { clsx } from "clsx";
import type { Alert } from "@/lib/types";
import {
  SEVERITY_BORDER_LEFT,
  SOURCE_COLOR,
  SOURCE_LABEL,
  relativeTime,
} from "@/lib/severity";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  alerts: Alert[];
  loading?: boolean;
}

function AlertSkeleton() {
  return (
    <div className="flex animate-pulse gap-3 rounded-lg border border-white/[0.06] bg-white/[0.03] border-l-2 border-l-slate-700 px-4 py-3">
      <div className="h-6 w-10 flex-shrink-0 rounded bg-white/[0.07]" />
      <div className="flex flex-1 flex-col gap-2 pt-0.5">
        <div className="h-3.5 w-3/4 rounded bg-white/[0.07]" />
        <div className="flex gap-2">
          <div className="h-2.5 w-20 rounded bg-white/[0.05]" />
          <div className="h-2.5 w-16 rounded bg-white/[0.05]" />
        </div>
      </div>
    </div>
  );
}

export function AlertFeed({ alerts, loading = false }: Props) {
  if (loading) {
    return (
      <div className="flex flex-col gap-2">
        {[...Array(5)].map((_, i) => <AlertSkeleton key={i} />)}
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="flex h-48 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/10 text-sm text-slate-500">
        <span className="text-2xl">📡</span>
        <span>No alerts</span>
        <span className="text-xs text-slate-600">Use Demo Scenarios to generate some</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {alerts.map((alert) => (
        <AlertRow key={alert.id} alert={alert} />
      ))}
    </div>
  );
}

function AlertRow({ alert }: { alert: Alert }) {
  const sourceLabel =
    SOURCE_LABEL[alert.source] ?? alert.source.toUpperCase().slice(0, 4);
  const sourceColor = SOURCE_COLOR[alert.source] ?? "bg-slate-500/20 text-slate-300";

  return (
    <div
      className={clsx(
        "group relative flex gap-3 rounded-lg border border-white/[0.06] bg-white/[0.03]",
        "border-l-2 px-4 py-3 transition-all hover:bg-white/[0.06]",
        SEVERITY_BORDER_LEFT[alert.severity] ?? "border-l-slate-500",
      )}
    >
      {/* Source chip */}
      <div className="flex-shrink-0 pt-0.5">
        <span
          className={clsx(
            "inline-flex h-6 w-10 items-center justify-center rounded text-[10px] font-bold",
            sourceColor,
          )}
        >
          {sourceLabel}
        </span>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="truncate text-sm font-medium text-slate-200 group-hover:text-white">
            {alert.title}
          </p>
          <SeverityBadge severity={alert.severity} size="sm" pulse />
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-500">
          <span className="font-mono">{alert.service_name}</span>
          <span>·</span>
          <span className="capitalize">{alert.environment}</span>
          <span>·</span>
          <span>{relativeTime(alert.timestamp)}</span>
          {alert.status !== "open" && (
            <>
              <span>·</span>
              <span
                className={clsx(
                  "capitalize",
                  alert.status === "resolved" && "text-green-500",
                  alert.status === "acknowledged" && "text-yellow-500",
                )}
              >
                {alert.status}
              </span>
            </>
          )}
        </div>

        {alert.description && (
          <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-slate-500">
            {alert.description}
          </p>
        )}
      </div>
    </div>
  );
}
