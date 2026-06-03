"use client";

import { clsx } from "clsx";
import {
  AlertTriangle,
  ChevronRight,
  Code2,
  Globe,
  Server,
  Tag,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { fetchAlert } from "@/lib/api";
import {
  SEVERITY_BADGE,
  SEVERITY_BORDER_LEFT,
  SOURCE_COLOR,
  SOURCE_LABEL,
  relativeTime,
} from "@/lib/severity";
import type { Alert } from "@/lib/types";
import { SeverityBadge } from "@/components/SeverityBadge";

interface Props {
  alertId: number | null;
  onClose: () => void;
}

const MAX_JSON_DEPTH = 6;

function JsonTree({ data, depth = 0 }: { data: unknown; depth?: number }) {
  const [collapsed, setCollapsed] = useState(depth > 1);

  // Hard cap on recursion depth — prevents stack overflow on pathological payloads
  if (depth >= MAX_JSON_DEPTH) {
    return (
      <span className="cursor-default text-slate-600" title="Depth limit reached">
        {typeof data === "object" && data !== null ? "{…}" : String(data)}
      </span>
    );
  }

  if (data === null || data === undefined) {
    return <span className="text-slate-500">null</span>;
  }
  if (typeof data === "boolean") {
    return <span className="text-yellow-400">{String(data)}</span>;
  }
  if (typeof data === "number") {
    return <span className="text-blue-400">{data}</span>;
  }
  if (typeof data === "string") {
    return <span className="text-green-400">"{data}"</span>;
  }
  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-slate-500">[]</span>;
    if (collapsed) {
      return (
        <button
          onClick={() => setCollapsed(false)}
          className="text-slate-400 hover:text-white"
        >
          [{data.length} items…]
        </button>
      );
    }
    return (
      <span>
        <button onClick={() => setCollapsed(true)} className="text-slate-400 hover:text-white">
          [
        </button>
        <div className="ml-4">
          {data.map((item, i) => (
            <div key={i}>
              <JsonTree data={item} depth={depth + 1} />
              {i < data.length - 1 && <span className="text-slate-600">,</span>}
            </div>
          ))}
        </div>
        <span className="text-slate-400">]</span>
      </span>
    );
  }
  if (typeof data === "object") {
    const entries = Object.entries(data as Record<string, unknown>);
    if (entries.length === 0) return <span className="text-slate-500">{"{}"}</span>;
    if (collapsed) {
      return (
        <button
          onClick={() => setCollapsed(false)}
          className="text-slate-400 hover:text-white"
        >
          {"{"}…{entries.length} keys{"}"}
        </button>
      );
    }
    return (
      <span>
        <button onClick={() => setCollapsed(true)} className="text-slate-400 hover:text-white">
          {"{"}
        </button>
        <div className="ml-4">
          {entries.map(([k, v], i) => (
            <div key={k} className="flex gap-1.5">
              <span className="text-purple-400">"{k}"</span>
              <span className="text-slate-600">:</span>
              <JsonTree data={v} depth={depth + 1} />
              {i < entries.length - 1 && <span className="text-slate-600">,</span>}
            </div>
          ))}
        </div>
        <span className="text-slate-400">{"}"}</span>
      </span>
    );
  }
  return <span className="text-slate-400">{String(data)}</span>;
}

export function AlertDrawer({ alertId, onClose }: Props) {
  const [alert, setAlert] = useState<Alert | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!alertId) return;
    setLoading(true);
    setAlert(null);
    setError(null);
    fetchAlert(alertId)
      .then(setAlert)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [alertId]);

  const isOpen = alertId !== null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={clsx(
          "fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-200",
          isOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={clsx(
          "fixed right-0 top-0 z-50 flex h-full w-full max-w-lg flex-col bg-[#0d0d1e] shadow-2xl",
          "border-l border-white/[0.08] transition-transform duration-300 ease-out",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {/* Header */}
        <div className="flex flex-shrink-0 items-center justify-between border-b border-white/[0.08] px-6 py-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-400" />
            <h2 className="text-sm font-semibold text-white">Alert Details</h2>
            {alert && (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-mono text-slate-400">
                #{alert.id}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/10 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex h-32 items-center justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500/30 border-t-indigo-500" />
            </div>
          )}

          {error && (
            <div className="m-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {alert && (
            <div className="space-y-0 divide-y divide-white/[0.05]">
              {/* Title block */}
              <div className="px-6 py-5">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span
                    className={clsx(
                      "rounded px-2 py-0.5 text-[10px] font-bold uppercase",
                      SOURCE_COLOR[alert.source] ?? "bg-slate-500/20 text-slate-400",
                    )}
                  >
                    {SOURCE_LABEL[alert.source] ?? alert.source}
                  </span>
                  <SeverityBadge severity={alert.severity} size="sm" pulse />
                  <span
                    className={clsx(
                      "rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase",
                      alert.status === "open"
                        ? "border-red-500/30 bg-red-500/10 text-red-400"
                        : alert.status === "resolved"
                        ? "border-green-500/30 bg-green-500/10 text-green-400"
                        : "border-slate-500/30 bg-slate-500/10 text-slate-400",
                    )}
                  >
                    {alert.status}
                  </span>
                </div>
                <h3 className="text-sm font-semibold leading-snug text-white">
                  {alert.title}
                </h3>
                {alert.description && (
                  <p className="mt-2 text-xs leading-relaxed text-slate-400">
                    {alert.description}
                  </p>
                )}
              </div>

              {/* Key-value rows */}
              <div className="divide-y divide-white/[0.04]">
                {[
                  {
                    icon: <Server className="h-3.5 w-3.5" />,
                    label: "Service",
                    value: (
                      <span className="font-mono text-white">{alert.service_name}</span>
                    ),
                  },
                  {
                    icon: <Globe className="h-3.5 w-3.5" />,
                    label: "Environment",
                    value: (
                      <span className="capitalize text-slate-300">{alert.environment}</span>
                    ),
                  },
                  {
                    icon: <Tag className="h-3.5 w-3.5" />,
                    label: "Source",
                    value: (
                      <span
                        className={clsx(
                          "rounded px-2 py-0.5 text-[10px] font-bold uppercase",
                          SOURCE_COLOR[alert.source] ?? "bg-slate-500/20 text-slate-400",
                        )}
                      >
                        {alert.source}
                      </span>
                    ),
                  },
                  {
                    icon: <ChevronRight className="h-3.5 w-3.5" />,
                    label: "Fired at",
                    value: (
                      <span className="text-slate-300">
                        {new Date(alert.timestamp).toLocaleString()}
                      </span>
                    ),
                  },
                  {
                    icon: <ChevronRight className="h-3.5 w-3.5" />,
                    label: "Received",
                    value: (
                      <span className="text-slate-300">
                        {relativeTime(alert.created_at)}
                      </span>
                    ),
                  },
                ].map((row) => (
                  <div
                    key={row.label}
                    className="flex items-center justify-between gap-3 px-6 py-2.5"
                  >
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      {row.icon}
                      {row.label}
                    </div>
                    <div className="text-xs">{row.value}</div>
                  </div>
                ))}
              </div>

              {/* Raw payload */}
              {alert.raw_payload && (
                <div className="px-6 py-5">
                  <div className="mb-3 flex items-center gap-2">
                    <Code2 className="h-3.5 w-3.5 text-slate-500" />
                    <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                      Raw Payload
                    </h4>
                  </div>
                  <div className="overflow-x-auto rounded-lg border border-white/[0.07] bg-[#080812] px-4 py-3 font-mono text-[11px] leading-5">
                    <JsonTree data={alert.raw_payload} />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
