"use client";

import { clsx } from "clsx";
import { Bot, LogOut, Zap } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
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

type AlertFilter = "all" | "open" | "critical";
type IncidentFilter = "all" | "active" | "resolved";

export default function DashboardPage() {
  const { status, alerts, incidents, toasts, dismissToast } = useWebSocket();
  const router = useRouter();
  const user = getStoredUser();

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [alertFilter, setAlertFilter] = useState<AlertFilter>("open");
  const [incidentFilter, setIncidentFilter] = useState<IncidentFilter>("active");

  // Derived data
  const filteredAlerts = alerts.filter((a) => {
    if (alertFilter === "open") return a.status === "open";
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

  // Keep selected incident in sync with live updates
  const liveSelected = selectedIncident
    ? incidents.find((i) => i.id === selectedIncident.id) ?? selectedIncident
    : null;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#0a0a15]">
      {/* ── Top Nav ── */}
      <nav className="flex flex-shrink-0 items-center justify-between border-b border-white/[0.07] bg-[#0d0d1e] px-6 py-3">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/20">
              <Bot className="h-4 w-4 text-indigo-400" />
            </div>
            <span className="text-sm font-semibold text-white">AI Ops Copilot</span>
          </Link>
          <div className="hidden items-center gap-3 text-xs sm:flex">
            <span className="text-slate-300">Dashboard</span>
            <Link href="/integrations" className="text-slate-500 hover:text-slate-300">
              Integrations
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ConnectionStatus status={status} />
          {user && (
            <span className="hidden text-xs text-slate-500 sm:block">
              <span className="text-slate-400">{user.org_name}</span>
              {" · "}
              {user.email}
            </span>
          )}
          <button
            onClick={handleLogout}
            title="Sign out"
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-white/[0.08] hover:text-white"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </nav>

      {/* ── Disconnected banner ── */}
      {status === "disconnected" && (
        <div className="flex flex-shrink-0 items-center justify-center gap-2 border-b border-red-500/20 bg-red-500/[0.07] px-4 py-2 text-xs text-red-400">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          Real-time feed disconnected — reconnecting…
        </div>
      )}

      {/* ── Body ── */}
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
        {/* Stats row */}
        <StatsBar alerts={alerts} incidents={incidents} loading={status === "connecting" && alerts.length === 0} />

        {/* Demo launcher */}
        <DemoLauncher />

        {/* Main 2-col layout */}
        <div
          className={clsx(
            "grid min-h-0 flex-1 gap-4",
            liveSelected ? "grid-cols-1 lg:grid-cols-[1fr_400px]" : "grid-cols-1 lg:grid-cols-2",
          )}
        >
          {/* ── Left: Alert Feed ── */}
          <Panel
            title="Alert Feed"
            count={filteredAlerts.length}
            icon={<Zap className="h-3.5 w-3.5" />}
            filters={
              <FilterTabs
                options={[
                  { id: "open", label: "Open" },
                  { id: "critical", label: "Critical" },
                  { id: "all", label: "All" },
                ]}
                active={alertFilter}
                onChange={(v) => setAlertFilter(v as AlertFilter)}
              />
            }
          >
            <AlertFeed
              alerts={filteredAlerts}
              loading={status === "connecting" && alerts.length === 0}
            />
          </Panel>

          {/* ── Right: Incidents ── */}
          <Panel
            title="Incidents"
            count={filteredIncidents.length}
            filters={
              <FilterTabs
                options={[
                  { id: "active", label: "Active" },
                  { id: "all", label: "All" },
                  { id: "resolved", label: "Resolved" },
                ]}
                active={incidentFilter}
                onChange={(v) => setIncidentFilter(v as IncidentFilter)}
              />
            }
          >
            {filteredIncidents.length === 0 ? (
              <div className="flex h-48 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/10 text-sm text-slate-500">
                <span className="text-2xl">✅</span>
                No active incidents
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {filteredIncidents.map((inc) => (
                  <IncidentCard
                    key={inc.id}
                    incident={inc}
                    selected={liveSelected?.id === inc.id}
                    onClick={() =>
                      setSelectedIncident(
                        liveSelected?.id === inc.id ? null : inc,
                      )
                    }
                  />
                ))}
              </div>
            )}
          </Panel>

          {/* ── Detail panel (appears when incident selected) ── */}
          {liveSelected && (
            <div className="lg:col-start-2 lg:row-start-1 lg:col-span-1">
              <IncidentDetail
                incident={liveSelected}
                onClose={() => setSelectedIncident(null)}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Toast notifications ── */}
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────

function Panel({
  title,
  count,
  icon,
  filters,
  children,
}: {
  title: string;
  count?: number;
  icon?: React.ReactNode;
  filters?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-white/[0.07] bg-white/[0.02] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {icon && <span className="text-slate-500">{icon}</span>}
          <h2 className="text-sm font-semibold text-white">{title}</h2>
          {count !== undefined && (
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs tabular-nums text-slate-400">
              {count}
            </span>
          )}
        </div>
        {filters}
      </div>

      <div className="overflow-y-auto">{children}</div>
    </div>
  );
}

function FilterTabs({
  options,
  active,
  onChange,
}: {
  options: { id: string; label: string }[];
  active: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-0.5 rounded-lg bg-white/[0.05] p-0.5">
      {options.map((opt) => (
        <button
          key={opt.id}
          onClick={() => onChange(opt.id)}
          className={clsx(
            "rounded-md px-3 py-1 text-xs font-medium transition",
            active === opt.id
              ? "bg-white/10 text-white"
              : "text-slate-500 hover:text-slate-300",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
