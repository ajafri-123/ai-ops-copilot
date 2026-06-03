import { Activity, AlertTriangle, Bot, Zap } from "lucide-react";
import Link from "next/link";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchHealth } from "@/lib/api";

async function getBackendHealth() {
  try {
    return await fetchHealth();
  } catch {
    return null;
  }
}

const features = [
  {
    icon: AlertTriangle,
    title: "Alert Ingestion",
    description:
      "Ingest infrastructure alerts from PagerDuty, Datadog, Prometheus, and custom webhooks.",
  },
  {
    icon: Activity,
    title: "Incident Correlation",
    description:
      "Automatically group related alerts into incidents using time-window and service-graph correlation.",
  },
  {
    icon: Bot,
    title: "AI Root-Cause Analysis",
    description:
      "LLM-powered analysis surfaces probable root causes and ranks remediation steps by confidence.",
  },
  {
    icon: Zap,
    title: "Real-Time Updates",
    description:
      "WebSocket-driven dashboard pushes incident state changes to every connected operator instantly.",
  },
];

export default async function HomePage() {
  const health = await getBackendHealth();

  return (
    <main className="flex min-h-screen flex-col">
      {/* ── Nav ── */}
      <nav className="border-b border-white/10 bg-white/5 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-brand-500" />
            <span className="text-lg font-semibold tracking-tight text-white">
              AI Ops Copilot
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <span>API</span>
            {health ? (
              <StatusBadge status={health.status} />
            ) : (
              <StatusBadge status="error" />
            )}
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-900/40 via-transparent to-transparent" />

        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand-500/30 bg-brand-500/10 px-4 py-1.5 text-sm text-brand-500">
          <Zap className="h-3.5 w-3.5" />
          AI-Powered Incident Response
        </div>

        <h1 className="max-w-3xl text-5xl font-bold tracking-tight text-white sm:text-6xl">
          Resolve incidents{" "}
          <span className="bg-gradient-to-r from-brand-500 to-violet-400 bg-clip-text text-transparent">
            10× faster
          </span>{" "}
          with AI
        </h1>

        <p className="mt-6 max-w-2xl text-lg text-slate-400">
          AI Ops Copilot ingests your infrastructure alerts, correlates related
          events, and delivers AI-generated root-cause analysis and remediation
          steps—right when your on-call team needs them.
        </p>

        <div className="mt-10 flex gap-4">
          <Link
            href="/dashboard"
            className="rounded-lg bg-brand-500 px-6 py-3 text-sm font-medium text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-500/90"
          >
            Open Dashboard →
          </Link>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-white/10 bg-white/5 px-6 py-3 text-sm font-medium text-slate-300 transition hover:bg-white/10"
          >
            API Docs
          </a>
        </div>
      </section>

      {/* ── Feature grid ── */}
      <section className="border-t border-white/10 bg-white/[0.02] px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <h2 className="mb-12 text-center text-3xl font-bold text-white">
            Everything your on-call team needs
          </h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="rounded-xl border border-white/10 bg-white/5 p-6 transition hover:border-brand-500/40 hover:bg-brand-500/5"
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-500/10">
                  <Icon className="h-5 w-5 text-brand-500" />
                </div>
                <h3 className="mb-2 font-semibold text-white">{title}</h3>
                <p className="text-sm leading-relaxed text-slate-400">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Backend status detail ── */}
      {health && (
        <section className="border-t border-white/10 px-6 py-10">
          <div className="mx-auto max-w-7xl">
            <h3 className="mb-4 text-sm font-medium uppercase tracking-widest text-slate-500">
              Service Health
            </h3>
            <div className="flex flex-wrap gap-4">
              {Object.entries(health.services).map(([svc, status]) => (
                <div
                  key={svc}
                  className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm"
                >
                  <span className="capitalize text-slate-300">{svc}</span>
                  <StatusBadge status={status === "ok" ? "ok" : "error"} />
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Footer ── */}
      <footer className="border-t border-white/10 px-6 py-6 text-center text-xs text-slate-600">
        AI Ops Copilot v0.1.0 — built with Next.js · FastAPI · PostgreSQL · Redis
      </footer>
    </main>
  );
}
