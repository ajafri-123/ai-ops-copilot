"use client";

import { clsx } from "clsx";
import { Loader2, Play, Terminal } from "lucide-react";
import { useState } from "react";
import { triggerDemoScenario } from "@/lib/api";

const SCENARIOS = [
  { id: "database_overload",  label: "DB Overload",   color: "text-red-400",    bg: "bg-red-500/[0.07]",    border: "border-red-500/20"    },
  { id: "memory_leak",        label: "Memory Leak",   color: "text-orange-400", bg: "bg-orange-500/[0.07]", border: "border-orange-500/20" },
  { id: "deployment_failure", label: "Bad Deploy",    color: "text-amber-400",  bg: "bg-amber-500/[0.07]",  border: "border-amber-500/20"  },
  { id: "network_partition",  label: "AZ Outage",     color: "text-purple-400", bg: "bg-purple-500/[0.07]", border: "border-purple-500/20" },
  { id: "queue_backlog",      label: "Queue Backlog", color: "text-blue-400",   bg: "bg-blue-500/[0.07]",   border: "border-blue-500/20"   },
];

export function DemoLauncher() {
  const [loading,    setLoading]    = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ scenario: string; alerts: number; incidents: number } | null>(null);

  const run = async (scenarioId: string) => {
    setLoading(scenarioId);
    setLastResult(null);
    try {
      const result = await triggerDemoScenario(scenarioId);
      setLastResult({ scenario: scenarioId, alerts: result.alerts_created, incidents: result.incidents_touched.length });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="rounded-xl border border-cyan-500/[0.08] bg-[#081320] p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5 text-cyan-500" />
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
            Demo Scenarios
          </h3>
        </div>
        {lastResult && (
          <span className="font-mono text-[10px] text-green-400">
            +{lastResult.alerts} alerts · {lastResult.incidents} incident{lastResult.incidents !== 1 ? "s" : ""}
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 gap-1.5">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => run(s.id)}
            disabled={loading !== null}
            className={clsx(
              "flex items-center gap-2.5 rounded-lg border px-3 py-2 text-xs font-medium transition",
              s.bg, s.border, s.color,
              "hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40",
              loading === s.id && "opacity-75",
            )}
          >
            {loading === s.id ? (
              <Loader2 className="h-3 w-3 animate-spin flex-shrink-0" />
            ) : (
              <Play className="h-3 w-3 flex-shrink-0" />
            )}
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
