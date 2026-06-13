"use client";

import { clsx } from "clsx";
import {
  AlertTriangle,
  Bot,
  ChevronDown,
  ChevronRight,
  LogOut,
  Plug,
  RefreshCw,
  Send,
  Unplug,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  fetchIntegrations,
  patchIntegration,
  sendTestAlert,
} from "@/lib/api";
import { clearAuth, getStoredUser } from "@/lib/auth";
import type { Integration, IntegrationProvider, TestAlertResponse } from "@/lib/types";

// ─────────────────────────────────────────────
// Provider metadata (static display info)
// ─────────────────────────────────────────────

const PROVIDER_META: Record<
  IntegrationProvider,
  {
    label: string;
    description: string;
    color: string;        // Tailwind bg colour for icon badge
    iconColor: string;    // Tailwind text colour
    icon: string;         // emoji / letter used as fallback icon
    alertSource: string;
    capabilities: string[];
  }
> = {
  aws_cloudwatch: {
    label: "AWS CloudWatch",
    description: "Ingest CloudWatch alarms from EC2, RDS, ALB, SQS, Lambda and more. Alerts fire when metrics breach thresholds.",
    color: "bg-orange-500/15",
    iconColor: "text-orange-400",
    icon: "☁",
    alertSource: "aws",
    capabilities: ["CloudWatch Alarms", "RDS metrics", "ALB 5xx rates", "SQS queue depth", "ECS/EKS metrics"],
  },
  datadog: {
    label: "Datadog",
    description: "Stream monitor alerts, APM traces, and custom metrics. Includes p99 latency, error-rate, and anomaly detection monitors.",
    color: "bg-violet-500/15",
    iconColor: "text-violet-400",
    icon: "D",
    alertSource: "datadog",
    capabilities: ["Monitor alerts", "APM p99/p95 latency", "Error rate tracking", "Anomaly detection", "Custom metrics"],
  },
  sentry: {
    label: "Sentry",
    description: "Receive error and performance alerts from Sentry issues. Includes unhandled exceptions, regressions, and spike notifications.",
    color: "bg-pink-500/15",
    iconColor: "text-pink-400",
    icon: "S",
    alertSource: "sentry",
    capabilities: ["Unhandled exceptions", "Performance regressions", "Issue spikes", "New error detection", "Release health"],
  },
  github_actions: {
    label: "GitHub Actions",
    description: "Receive alerts from CI/CD pipeline failures, deployment events, security scans, and rollback triggers.",
    color: "bg-slate-500/15",
    iconColor: "text-slate-300",
    icon: "G",
    alertSource: "github_actions",
    capabilities: ["Pipeline failures", "Deploy events", "Security scans (Trivy)", "Canary rollbacks", "Test failures"],
  },
  kubernetes: {
    label: "Kubernetes",
    description: "Get notified about pod OOMKills, CrashLoopBackOffs, node NotReady, HPA scaling limits, and PVC provisioning failures.",
    color: "bg-blue-500/15",
    iconColor: "text-blue-400",
    icon: "K",
    alertSource: "kubernetes",
    capabilities: ["OOMKill / CrashLoopBackOff", "Node NotReady", "HPA max replicas", "PVC pending", "Resource pressure"],
  },
  slack: {
    label: "Slack",
    description: "Forward critical #incidents and #alerts channel messages into the incident pipeline. Ideal for manual escalations.",
    color: "bg-green-500/15",
    iconColor: "text-green-400",
    icon: "#",
    alertSource: "slack",
    capabilities: ["#incidents channel", "On-call escalations", "Manual alerts", "PagerDuty webhooks", "Bot notifications"],
  },
};

// ─────────────────────────────────────────────
// Status helpers
// ─────────────────────────────────────────────

function StatusPill({ status }: { status: Integration["status"] }) {
  if (status === "connected")
    return (
      <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-400">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        Connected
      </span>
    );
  if (status === "error")
    return (
      <span className="flex items-center gap-1 rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-medium text-red-400">
        <AlertTriangle className="h-3 w-3" />
        Error
      </span>
    );
  return (
    <span className="flex items-center gap-1 rounded-full bg-white/[0.06] px-2 py-0.5 text-xs font-medium text-slate-500">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
      Disconnected
    </span>
  );
}

function relativeTime(iso: string): string {
  if (typeof window === "undefined") return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ─────────────────────────────────────────────
// Toast
// ─────────────────────────────────────────────

interface Toast {
  id: number;
  type: "success" | "error" | "info";
  message: string;
  detail?: string;
}

let _toastId = 0;

function ToastList({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          onClick={() => onDismiss(t.id)}
          className={clsx(
            "pointer-events-auto flex max-w-sm cursor-pointer flex-col gap-0.5 rounded-xl border px-4 py-3 text-sm shadow-xl transition",
            t.type === "success" && "border-emerald-500/25 bg-[#0d1a14] text-emerald-300",
            t.type === "error" && "border-red-500/25 bg-[#1a0d0d] text-red-300",
            t.type === "info" && "border-indigo-500/25 bg-[#06101f] text-indigo-300",
          )}
        >
          <span className="font-medium">{t.message}</span>
          {t.detail && <span className="text-xs opacity-70">{t.detail}</span>}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// Integration Card
// ─────────────────────────────────────────────

function IntegrationCard({
  integration,
  onConnect,
  onDisconnect,
  onTestAlert,
}: {
  integration: Integration;
  onConnect: (id: number) => Promise<void>;
  onDisconnect: (id: number) => Promise<void>;
  onTestAlert: (id: number) => Promise<void>;
}) {
  const meta = PROVIDER_META[integration.provider];
  const [connecting, setConnecting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showPayload, setShowPayload] = useState(false);
  const isConnected = integration.status === "connected";

  async function handleConnect() {
    setConnecting(true);
    try {
      await onConnect(integration.id);
    } finally {
      setConnecting(false);
    }
  }

  async function handleDisconnect() {
    setConnecting(true);
    try {
      await onDisconnect(integration.id);
    } finally {
      setConnecting(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    try {
      await onTestAlert(integration.id);
    } finally {
      setTesting(false);
    }
  }

  const samplePayload = (integration.config?.sample_payload ?? null) as Record<
    string,
    unknown
  > | null;

  return (
    <div
      className={clsx(
        "flex flex-col gap-4 rounded-xl border p-5 transition",
        isConnected
          ? "border-white/[0.09] bg-white/[0.025]"
          : "border-white/[0.05] bg-white/[0.015]",
      )}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className={clsx(
              "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-base font-bold",
              meta.color,
              meta.iconColor,
            )}
          >
            {meta.icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{meta.label}</span>
              <StatusPill status={integration.status} />
            </div>
            {integration.last_sync && (
              <p className="mt-0.5 text-xs text-slate-600">
                Last sync {relativeTime(integration.last_sync)}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-xs leading-relaxed text-slate-500">{meta.description}</p>

      {/* Capabilities */}
      <div className="flex flex-wrap gap-1.5">
        {meta.capabilities.map((cap) => (
          <span
            key={cap}
            className="rounded-md bg-white/[0.05] px-2 py-0.5 text-[10px] text-slate-500"
          >
            {cap}
          </span>
        ))}
      </div>

      {/* Sample payload toggle */}
      {samplePayload && (
        <button
          onClick={() => setShowPayload((v) => !v)}
          className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-400"
        >
          {showPayload ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          Sample payload
        </button>
      )}
      {showPayload && samplePayload && (
        <pre className="overflow-x-auto rounded-lg bg-black/40 p-3 text-[10px] leading-relaxed text-slate-400">
          {JSON.stringify(samplePayload, null, 2)}
        </pre>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        {isConnected ? (
          <>
            <button
              onClick={handleTest}
              disabled={testing}
              className="flex items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/15 px-3 py-1.5 text-xs font-medium text-cyan-300 transition hover:bg-cyan-500/25 disabled:opacity-50"
            >
              {testing ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              {testing ? "Sending…" : "Send test alert"}
            </button>
            <button
              onClick={handleDisconnect}
              disabled={connecting}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-400 transition hover:bg-white/[0.08] hover:text-white disabled:opacity-50"
            >
              <Unplug className="h-3.5 w-3.5" />
              Disconnect
            </button>
          </>
        ) : (
          <button
            onClick={handleConnect}
            disabled={connecting}
            className="flex items-center gap-1.5 rounded-lg bg-white/[0.06] px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/[0.10] hover:text-white disabled:opacity-50"
          >
            {connecting ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Plug className="h-3.5 w-3.5" />
            )}
            {connecting ? "Connecting…" : "Connect"}
          </button>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────

export default function IntegrationsPage() {
  const router = useRouter();
  const [user, setUser] = useState<ReturnType<typeof getStoredUser>>(null);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  function addToast(toast: Omit<Toast, "id">) {
    const id = ++_toastId;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000);
  }

  function dismissToast(id: number) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  const load = useCallback(async () => {
    try {
      const data = await fetchIntegrations();
      setIntegrations(data);
    } catch {
      addToast({ type: "error", message: "Failed to load integrations" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleConnect(id: number) {
    try {
      const updated = await patchIntegration(id, { status: "connected" });
      setIntegrations((prev) => prev.map((i) => (i.id === id ? updated : i)));
      addToast({ type: "success", message: `${PROVIDER_META[updated.provider].label} connected` });
    } catch {
      addToast({ type: "error", message: "Connection failed" });
    }
  }

  async function handleDisconnect(id: number) {
    try {
      const updated = await patchIntegration(id, { status: "disconnected" });
      setIntegrations((prev) => prev.map((i) => (i.id === id ? updated : i)));
      addToast({ type: "info", message: `${PROVIDER_META[updated.provider].label} disconnected` });
    } catch {
      addToast({ type: "error", message: "Disconnect failed" });
    }
  }

  async function handleTestAlert(id: number) {
    try {
      const result = await sendTestAlert(id);
      addToast({
        type: "success",
        message: `Test alert sent → ${result.created_new_incident ? "New incident created" : "Correlated to existing incident"}`,
        detail: `"${result.alert_title}" · Incident #${result.incident_id}`,
      });
    } catch (err) {
      addToast({
        type: "error",
        message: err instanceof Error ? err.message : "Test alert failed",
      });
    }
  }

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  const connected = integrations.filter((i) => i.status === "connected").length;

  return (
    <div className="flex min-h-screen flex-col bg-[#020913]">
      {/* Nav */}
      <nav className="flex flex-shrink-0 items-center justify-between border-b border-cyan-500/[0.08] bg-[#06101f] px-6 py-3">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/20">
              <Bot className="h-4 w-4 text-indigo-400" />
            </div>
            <span className="text-sm font-semibold text-white">AI Ops Copilot</span>
          </Link>
          <div className="hidden items-center gap-3 text-xs sm:flex">
            <Link href="/dashboard" className="text-slate-500 hover:text-slate-300">
              Dashboard
            </Link>
            <span className="text-slate-700">/</span>
            <span className="text-slate-300">Integrations</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {user && (
            <span className="hidden text-xs text-slate-500 sm:block">
              <span className="text-slate-400">{user.org_name}</span>
              {" · "}
              {user.email}
            </span>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-white/[0.08] hover:text-white"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </nav>

      {/* Body */}
      <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        {/* Page header */}
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-white">Integrations</h1>
            <p className="mt-1 text-sm text-slate-500">
              Connect your monitoring and alerting tools to automatically ingest alerts and trigger
              the correlation engine.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-cyan-500/[0.08] bg-white/[0.03] px-4 py-2.5 text-sm">
            <span className="text-slate-500">Active</span>
            <span className="font-semibold text-white">{connected}</span>
            <span className="text-slate-600">/</span>
            <span className="text-slate-500">{integrations.length}</span>
          </div>
        </div>

        {/* How it works bar */}
        <div className="mb-6 flex flex-wrap items-center gap-2 rounded-xl border border-indigo-500/20 bg-indigo-500/[0.04] px-4 py-3 text-xs text-slate-400">
          <span className="flex items-center gap-1.5 font-medium text-indigo-400">
            <Zap className="h-3.5 w-3.5" />
            How it works
          </span>
          <span className="text-slate-600">·</span>
          <span>Connect an integration</span>
          <ChevronRight className="h-3 w-3 text-slate-600" />
          <span>Send a test alert</span>
          <ChevronRight className="h-3 w-3 text-slate-600" />
          <span>Watch the correlation engine create or update an incident</span>
          <ChevronRight className="h-3 w-3 text-slate-600" />
          <Link href="/dashboard" className="text-cyan-400 hover:text-cyan-300">
            See it live on the dashboard →
          </Link>
        </div>

        {/* Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-24 text-sm text-slate-600">
            Loading integrations…
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {integrations.map((integration) => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                onConnect={handleConnect}
                onDisconnect={handleDisconnect}
                onTestAlert={handleTestAlert}
              />
            ))}
          </div>
        )}
      </div>

      <ToastList toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
