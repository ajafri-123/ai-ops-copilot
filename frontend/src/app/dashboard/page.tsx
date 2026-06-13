"use client";

import { clsx } from "clsx";
import { Bot, LogOut, LayoutDashboard, Plug } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertFeed } from "@/components/AlertFeed";
import { ConnectionStatus } from "@/components/ConnectionStatus";
import { DemoLauncher } from "@/components/DemoLauncher";
import { IncidentCard } from "@/components/IncidentCard";
import { IncidentDetail } from "@/components/IncidentDetail";
import { StatsBar } from "@/components/StatsBar";
import { ToastStack } from "@/components/ToastStack";
import { useWebSocket } from "@/hooks/useWebSocket";
import { clearAuth, getStoredUser } from "@/lib/auth";
import type { Incident } from "@/lib/types";

type AlertFilter    = "all" | "open" | "critical";
type IncidentFilter = "all" | "active" | "resolved";

export default function DashboardPage() {
  const { status, alerts, incidents, loading, toasts, dismissToast } = useWebSocket();
  const router = useRouter();
  const [user, setUser] = useState<ReturnType<typeof getStoredUser>>(null);

  useEffect(() => { setUser(getStoredUser()); }, []);

  function handleLogout() { clearAuth(); router.push("/login"); }

  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [alertFilter,    setAlertFilter]    = useState<AlertFilter>("open");
  const [incidentFilter, setIncidentFilter] = useState<IncidentFilter>("active");

  const filteredAlerts = alerts.filter((a) => {
    if (alertFilter === "open")     return a.status === "open";
    if (alertFilter === "critical") return a.severity === "critical";
    return true;
  });

  const filteredIncidents = incidents.filter((i) => {
    if (incidentFilter === "active")
      return ["open", "investigating", "identified", "monitoring"].includes(i.status);
    if (incidentFilter === "resolved")
      return ["resolved", "closed"].includes(i.status);
    return true;
  });

  const liveSelected = selectedIncident
    ? incidents.find((i) => i.id === selectedIncident.id) ?? selectedIncident
    : null;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#020913]">

      {/* ── Top Nav ── */}
      <nav className="relative flex flex-shrink-0 items-center justify-between border-b border-cyan-500/[0.1] bg-[#06101f] px-5 py-3">
        <div className="nav-scan-line" />

        <div className="flex items-center gap-5">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/[0.1] shadow-glow-cyan">
              <Bot className="h-3.5 w-3.5 text-cyan-400" />
            </div>
            <span className="text-sm font-semibold text-white">AI Ops Copilot</span>
          </Link>
          <div className="hidden items-center gap-1 sm:flex">
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-slate-300 bg-white/[0.05]"
            >
              <LayoutDashboard className="h-3 w-3" />
              Dashboard
            </Link>
            <Link
              href="/integrations"
              className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-white/[0.04] hover:text-slate-300"
            >
              <Plug className="h-3 w-3" />
              Integrations
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ConnectionStatus status={status} />
          {user && (
            <span className="hidden text-xs text-slate-600 sm:block font-mono">
              <span className="text-slate-400">{user.org_name}</span>
              {" · "}
              {user.email}
            </span>
          )}
          <button
            onClick={handleLogout}
            title="Sign out"
            className="flex items-center gap-1.5 rounded-lg border border-cyan-500/[0.1] bg-cyan-500/[0.04] px-2.5 py-1.5 text-xs text-slate-500 transition hover:border-cyan-500/20 hover:bg-cyan-500/[0.08] hover:text-slate-300"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </nav>

      {/* ── Disconnected banner ── */}
      {status === "disconnected" && (
        <div className="flex flex-shrink-0 items-center justify-center gap-2 border-b border-red-500/20 bg-red-500/[0.06] px-4 py-2 text-xs text-red-400">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          Real-time feed disconnected — reconnecting…
        </div>
      )}

      {/* ── Main layout ── */}
      <div className="flex min-h-0 flex-1 overflow-hidden">

        {/* Left sidebar */}
        <div className="flex w-72 flex-shrink-0 flex-col gap-4 overflow-y-auto border-r border-cyan-500/[0.07] bg-[#06101f] p-4 xl:w-80">
          <StatsBar alerts={alerts} incidents={incidents} loading={loading} />
          <DemoLauncher />

          {/* Incidents panel */}
          <div className="flex flex-1 flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
                Incidents
              </h2>
              <span className="font-mono text-[10px] text-slate-600">
                {filteredIncidents.length}
              </span>
            </div>

            {/* Filter pills */}
            <div className="flex gap-0.5 rounded-lg border border-cyan-500/[0.08] bg-[#020913] p-0.5">
              {(["active", "all", "resolved"] as IncidentFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setIncidentFilter(f)}
                  className={clsx(
                    "flex-1 rounded-md py-1 text-[10px] font-semibold uppercase tracking-wide transition",
                    incidentFilter === f
                      ? "bg-cyan-500/15 text-cyan-300"
                      : "text-slate-600 hover:text-slate-400",
                  )}
                >
                  {f}
                </button>
              ))}
            </div>

            {filteredIncidents.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-cyan-500/10 py-10 text-center">
                <span className="text-2xl">📡</span>
                <span className="text-xs text-slate-500">No incidents</span>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {filteredIncidents.map((inc) => (
                  <IncidentCard
                    key={inc.id}
                    incident={inc}
                    selected={liveSelected?.id === inc.id}
                    onClick={() =>
                      setSelectedIncident((prev) =>
                        prev?.id === inc.id ? null : inc,
                      )
                    }
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Center — alert feed */}
        <div className="flex min-w-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Alert Feed
            </h2>
            {/* Filter pills */}
            <div className="flex gap-0.5 rounded-lg border border-cyan-500/[0.08] bg-[#06101f] p-0.5">
              {(["open", "critical", "all"] as AlertFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setAlertFilter(f)}
                  className={clsx(
                    "rounded-md px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition",
                    alertFilter === f
                      ? "bg-cyan-500/15 text-cyan-300"
                      : "text-slate-600 hover:text-slate-400",
                  )}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
          <AlertFeed alerts={filteredAlerts} loading={loading} />
        </div>

        {/* Right — incident detail */}
        {liveSelected && (
          <div className="hidden w-[420px] flex-shrink-0 border-l border-cyan-500/[0.07] p-4 xl:block xl:w-[460px]">
            <IncidentDetail
              incident={liveSelected}
              onClose={() => setSelectedIncident(null)}
            />
          </div>
        )}
      </div>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
