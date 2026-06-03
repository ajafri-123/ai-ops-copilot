"use client";

import { clsx } from "clsx";
import { AlertTriangle, CheckCircle2, Flame, Radio } from "lucide-react";
import type { Alert, Incident } from "@/lib/types";

interface Props {
  alerts: Alert[];
  incidents: Incident[];
  loading?: boolean;
}

export function StatsBar({ alerts, incidents, loading = false }: Props) {
  const openAlerts = alerts.filter((a) => a.status === "open").length;
  const criticalAlerts = alerts.filter((a) => a.severity === "critical").length;
  const openIncidents = incidents.filter(
    (i) => i.status === "open" || i.status === "investigating",
  ).length;
  const resolvedToday = incidents.filter((i) => {
    if (i.status !== "resolved") return false;
    const updated = new Date(i.updated_at);
    const today = new Date();
    return updated.toDateString() === today.toDateString();
  }).length;

  const stats = [
    {
      label: "Open Alerts",
      value: openAlerts,
      icon: <Radio className="h-4 w-4" />,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
    },
    {
      label: "Critical",
      value: criticalAlerts,
      icon: <Flame className="h-4 w-4" />,
      color: "text-red-400",
      bg: "bg-red-500/10",
      highlight: criticalAlerts > 0,
    },
    {
      label: "Active Incidents",
      value: openIncidents,
      icon: <AlertTriangle className="h-4 w-4" />,
      color: "text-orange-400",
      bg: "bg-orange-500/10",
    },
    {
      label: "Resolved Today",
      value: resolvedToday,
      icon: <CheckCircle2 className="h-4 w-4" />,
      color: "text-green-400",
      bg: "bg-green-500/10",
    },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="flex items-center gap-3 rounded-xl border border-white/[0.07] bg-white/[0.03] px-4 py-3"
          >
            <div
              className={clsx(
                "flex h-9 w-9 flex-shrink-0 animate-pulse items-center justify-center rounded-lg opacity-30",
                stat.bg,
                stat.color,
              )}
            >
              {stat.icon}
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="h-5 w-8 animate-pulse rounded bg-white/10" />
              <div className="h-3 w-20 animate-pulse rounded bg-white/[0.06]" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className={clsx(
            "flex items-center gap-3 rounded-xl border border-white/[0.07] px-4 py-3",
            stat.highlight
              ? "border-red-500/30 bg-red-500/[0.08] shadow-[0_0_20px_rgba(239,68,68,0.08)]"
              : "bg-white/[0.03]",
          )}
        >
          <div
            className={clsx(
              "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg",
              stat.bg,
              stat.color,
            )}
          >
            {stat.icon}
          </div>
          <div>
            <p className="text-xl font-bold tabular-nums text-white">
              {stat.value}
            </p>
            <p className="text-xs text-slate-500">{stat.label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
