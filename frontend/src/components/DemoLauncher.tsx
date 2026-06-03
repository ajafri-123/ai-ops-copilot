"use client";

import { clsx } from "clsx";
import { Play, Loader2 } from "lucide-react";
import { useState } from "react";
import { triggerDemoScenario } from "@/lib/api";

const SCENARIOS = [
  { id: "database_overload", label: "DB Overload", color: "text-red-400" },
  { id: "memory_leak", label: "Memory Leak", color: "text-orange-400" },
  { id: "deployment_failure", label: "Bad Deploy", color: "text-yellow-400" },
  { id: "network_partition", label: "AZ Outage", color: "text-purple-400" },
  { id: "queue_backlog", label: "Queue Backlog", color: "text-blue-400" },
];

export function DemoLauncher() {
  const [loading, setLoading] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{
    scenario: string;
    alerts: number;
    incidents: number;
  } | null>(null);

  const run = async (scenarioId: string) => {
    setLoading(scenarioId);
    setLastResult(null);
    try {
      const result = await triggerDemoScenario(scenarioId);
      setLastResult({
        scenario: scenarioId,
        alerts: result.alerts_created,
        incidents: result.incidents_touched.length,
      });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Demo Scenarios
        </h3>
        {lastResult && (
          <span className="text-[10px] text-green-400">
            +{lastResult.alerts} alerts → {lastResult.incidents} incident(s)
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => run(s.id)}
            disabled={loading !== null}
            className={clsx(
              "inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.05]",
              "px-3 py-1.5 text-xs font-medium transition",
              "hover:border-white/20 hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-50",
              s.color,
              loading === s.id && "opacity-75",
            )}
          >
            {loading === s.id ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Play className="h-3 w-3" />
            )}
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
