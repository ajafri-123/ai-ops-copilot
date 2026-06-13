"use client";

import { clsx } from "clsx";
import {
  ArrowLeft,
  BrainCircuit,
  Clock,
  GitFork,
  LayoutDashboard,
  Loader2,
  Share2,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { AlertDrawer } from "@/components/incident/AlertDrawer";
import { AIPanel } from "@/components/incident/AIPanel";
import { IncidentMeta } from "@/components/incident/IncidentMeta";
import { IncidentTimeline } from "@/components/incident/IncidentTimeline";
import { ServiceGraphLoader as ServiceGraph } from "@/components/incident/ServiceGraphLoader";
import { fetchIncident, fetchIncidentGraph } from "@/lib/api";
import type { Incident, RCAResult, ServiceGraphResponse } from "@/lib/types";

type Tab = "overview" | "timeline" | "ai";

export default function IncidentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const incidentId = parseInt(id, 10);

  const [incident, setIncident] = useState<Incident | null>(null);
  const [graph, setGraph] = useState<ServiceGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [drawerAlertId, setDrawerAlertId] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!Number.isInteger(incidentId) || incidentId <= 0) {
      setError("Invalid incident ID");
      setLoading(false);
      return;
    }
    try {
      const [inc, g] = await Promise.all([
        fetchIncident(incidentId),
        fetchIncidentGraph(incidentId),
      ]);
      setIncident(inc);
      setGraph(g);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load incident");
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => { load(); }, [load]);

  const handleAnalyzed = useCallback(
    (result: RCAResult) => {
      if (!incident) return;
      setIncident((prev) =>
        prev
          ? { ...prev, root_cause: result.root_cause, summary: result.summary, remediation_steps: result.remediation_steps }
          : prev,
      );
    },
    [incident],
  );

  const hasAiData = !!(incident?.root_cause || incident?.remediation_steps?.length);
  const alertCount = incident?.events.filter((e) => e.event_type === "alert_added").length ?? 0;

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#020913]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-cyan-500" />
          <p className="text-sm text-slate-500">Loading incident…</p>
        </div>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-[#020913]">
        <p className="text-sm text-red-400">{error ?? "Incident not found"}</p>
        <Link href="/dashboard" className="text-xs text-cyan-400 hover:underline">
          ← Back to dashboard
        </Link>
      </div>
    );
  }

  const TABS = [
    { id: "overview" as Tab, label: "Overview",    icon: <LayoutDashboard className="h-3.5 w-3.5" /> },
    { id: "timeline" as Tab, label: "Timeline",    icon: <Clock className="h-3.5 w-3.5" />, count: incident.events.length },
    { id: "ai"       as Tab, label: "AI Analysis", icon: <BrainCircuit className="h-3.5 w-3.5" />, dot: hasAiData },
  ];

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#020913] text-slate-300">

      {/* ── Top nav ── */}
      <header className="relative flex flex-shrink-0 items-center justify-between border-b border-cyan-500/[0.1] bg-[#06101f] px-6 py-3">
        <div className="nav-scan-line" />
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-slate-500 transition hover:bg-white/[0.06] hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Dashboard
          </Link>
          <div className="h-4 w-px bg-cyan-500/10" />
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-slate-600">
              INC-{String(incident.id).padStart(4, "0")}
            </span>
            <span className="h-1 w-1 rounded-full bg-slate-700" />
            <span className="max-w-sm truncate text-sm font-medium text-white">
              {incident.title}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="rounded-lg border border-cyan-500/[0.1] bg-cyan-500/[0.04] p-2 text-slate-500 transition hover:bg-cyan-500/[0.08] hover:text-slate-300"
            title="Refresh"
          >
            <GitFork className="h-3.5 w-3.5" />
          </button>
          <button className="rounded-lg border border-cyan-500/[0.1] bg-cyan-500/[0.04] p-2 text-slate-500 transition hover:bg-cyan-500/[0.08] hover:text-slate-300">
            <Share2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      {/* ── Tab bar ── */}
      <div className="flex flex-shrink-0 items-center border-b border-cyan-500/[0.08] bg-[#06101f] px-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "relative flex items-center gap-1.5 px-4 py-3 text-xs font-medium transition",
              activeTab === tab.id
                ? "text-white after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:rounded-full after:bg-cyan-500"
                : "text-slate-500 hover:text-slate-300",
            )}
          >
            {tab.icon}
            {tab.label}
            {"count" in tab && tab.count !== undefined && (
              <span className="rounded-full bg-white/[0.08] px-1.5 py-0.5 text-[10px] tabular-nums text-slate-400">
                {tab.count}
              </span>
            )}
            {"dot" in tab && tab.dot && (
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            )}
          </button>
        ))}
      </div>

      {/* ── Main content ── */}
      <div className="flex min-h-0 flex-1">
        {/* Left sidebar */}
        <aside className="hidden w-72 flex-shrink-0 overflow-y-auto border-r border-cyan-500/[0.07] p-4 lg:block">
          <IncidentMeta incident={incident} />
        </aside>

        <main className="flex min-h-0 flex-1 overflow-hidden">

          {/* Overview */}
          {activeTab === "overview" && (
            <div className="flex flex-1 flex-col gap-0 overflow-y-auto">
              <div className="block border-b border-cyan-500/[0.07] p-4 lg:hidden">
                <IncidentMeta incident={incident} />
              </div>

              {incident.summary && (
                <div className="border-b border-cyan-500/[0.07] px-6 py-5">
                  <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                    Summary
                  </h3>
                  <p className="text-sm leading-relaxed text-slate-300">{incident.summary}</p>
                </div>
              )}

              <div className="flex flex-col border-b border-cyan-500/[0.07]">
                <div className="flex items-center justify-between border-b border-cyan-500/[0.07] px-6 py-3">
                  <div className="flex items-center gap-2">
                    <GitFork className="h-3.5 w-3.5 text-cyan-500/60" />
                    <h3 className="text-xs font-semibold text-white">Service Dependency Graph</h3>
                    {incident.affected_services && (
                      <span className="rounded-full border border-cyan-500/15 bg-cyan-500/[0.07] px-2 py-0.5 text-[10px] tabular-nums text-cyan-400">
                        {incident.affected_services.length} affected
                      </span>
                    )}
                  </div>
                </div>
                <div className="h-72">
                  {graph ? (
                    <ServiceGraph graph={graph} />
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <Loader2 className="h-5 w-5 animate-spin text-cyan-500/40" />
                    </div>
                  )}
                </div>
              </div>

              <div className="px-6 py-5">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="h-3.5 w-3.5 text-amber-500/70" />
                    <h3 className="text-xs font-semibold text-white">Correlated Alerts</h3>
                    <span className="rounded-full border border-cyan-500/15 bg-cyan-500/[0.07] px-2 py-0.5 text-[10px] text-cyan-400">
                      {alertCount}
                    </span>
                  </div>
                  <button
                    onClick={() => setActiveTab("timeline")}
                    className="text-xs text-cyan-400 hover:underline"
                  >
                    View full timeline →
                  </button>
                </div>

                <div className="space-y-1.5">
                  {incident.events
                    .filter((e) => e.event_type === "alert_added")
                    .slice(0, 5)
                    .map((ev) => (
                      <button
                        key={ev.id}
                        onClick={() => ev.alert_id && setDrawerAlertId(ev.alert_id)}
                        className="group w-full rounded-lg border border-cyan-500/[0.07] bg-[#081320] px-4 py-3 text-left transition hover:border-cyan-500/15 hover:bg-[#0c1828]"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-xs text-slate-300 group-hover:text-white line-clamp-2">
                            {ev.message}
                          </p>
                          <span className="flex-shrink-0 font-mono text-[10px] text-slate-600">
                            {ev.alert_id ? `#${ev.alert_id}` : ""}
                          </span>
                        </div>
                        {ev.alert_id && (
                          <p className="mt-1 text-[10px] text-cyan-500/60">
                            Click to view raw alert →
                          </p>
                        )}
                      </button>
                    ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "timeline" && (
            <div className="flex-1 overflow-hidden p-6">
              <IncidentTimeline events={incident.events} onAlertClick={(id) => setDrawerAlertId(id)} />
            </div>
          )}

          {activeTab === "ai" && (
            <div className="flex-1 overflow-y-auto p-6">
              <AIPanel incident={incident} onAnalyzed={handleAnalyzed} />
            </div>
          )}
        </main>
      </div>

      <AlertDrawer alertId={drawerAlertId} onClose={() => setDrawerAlertId(null)} />
    </div>
  );
}
