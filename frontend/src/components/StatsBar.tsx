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
  const openAlerts     = alerts.filter((a) => a.status === "open").length;
  const criticalAlerts = alerts.filter((a) => a.severity === "critical").length;
  const openIncidents  = incidents.filter(
    (i) => i.status === "open" || i.status === "investigating",
  ).length;
  const resolvedToday  = typeof window === "undefined" ? 0 : incidents.filter((i) => {
    if (i.status !== "resolved") return false;
    const updated = new Date(i.updated_at);
    const today   = new Date();
    return updated.toDateString() === today.toDateString();
  }).length;

  const stats = [
    {
      label: "Open Alerts",
      value: openAlerts,
      icon: <Radio className="h-4 w-4" />,
      color:   "text-cyan-400",
      bg:      "bg-cyan-500/10",
      border:  "border-cyan-500/20",
      glow:    openAlerts > 0,
      glowClass: "shadow-glow-cyan",
    },
    {
      label: "Critical",
      value: criticalAlerts,
      icon: <Flame className="h-4 w-4" />,
      color:     "text-red-400",
      bg:        "bg-red-500/10",
      border:    "border-red-500/20",
      glow:      criticalAlerts > 0,
      glowClass: "shadow-glow-red",
    },
    {
      label: "Active Incidents",
      value: openIncidents,
      icon: <AlertTriangle className="h-4 w-4" />,
      color:   "text-orange-400",
      bg:      "bg-orange-500/10",
      border:  "border-orange-500/20",
      glow:    openIncidents > 0,
      glowClass: "shadow-glow-orange",
    },
    {
      label: "Resolved Today",
      value: resolvedToday,
      icon: <CheckCircle2 className="h-4 w-4" />,
      color:   "text-green-400",
      bg:      "bg-green-500/10",
      border:  "border-green-500/20",
      glow:    false,
      glowClass: "",
    },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-2">
        {stats.map((s) => (
          <div
            key={s.label}
            className="flex flex-col gap-2 rounded-xl border border-cyan-500/[0.06] bg-[#081320] p-3 animate-pulse"
          >
            <div className={clsx("h-7 w-7 rounded-lg opacity-20", s.bg)} />
            <div className="h-5 w-10 rounded bg-white/[0.06]" />
            <div className="h-2.5 w-16 rounded bg-white/[0.04]" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      {stats.map((s) => (
        <div
          key={s.label}
          className={clsx(
            "flex flex-col gap-2 rounded-xl border bg-[#081320] p-3 transition-shadow",
            s.border,
            s.glow && s.glowClass,
          )}
        >
          <div className={clsx("flex h-7 w-7 items-center justify-center rounded-lg border", s.bg, s.border, s.color)}>
            {s.icon}
          </div>
          <p className={clsx("text-2xl font-bold tabular-nums leading-none", s.glow ? "text-white" : "text-slate-300")}>
            {s.value}
          </p>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600">{s.label}</p>
        </div>
      ))}
    </div>
  );
}
