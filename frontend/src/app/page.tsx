import { Activity, AlertTriangle, Bot, Radio, Shield, Zap } from "lucide-react";
import Link from "next/link";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchHealth } from "@/lib/api";

async function getBackendHealth() {
  try { return await fetchHealth(); } catch { return null; }
}

const features = [
  {
    icon: AlertTriangle,
    title: "Alert Ingestion",
    description: "Ingest alerts from PagerDuty, Datadog, Prometheus, and custom webhooks via a single REST endpoint.",
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
  },
  {
    icon: Activity,
    title: "Incident Correlation",
    description: "Time-window and service-graph correlation automatically groups related alerts into a single incident.",
    color: "text-cyan-400",
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/20",
  },
  {
    icon: Bot,
    title: "AI Root-Cause Analysis",
    description: "GPT-4o-mini surfaces probable root causes, reconstructs the event timeline, and ranks remediation steps.",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    border: "border-indigo-500/20",
  },
  {
    icon: Zap,
    title: "Real-Time Dashboard",
    description: "WebSocket-driven updates push incident state changes to every connected operator in milliseconds.",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
  },
];

const mockIncidents = [
  { id: "0047", sev: "CRITICAL", color: "text-red-400", dot: "bg-red-500", title: "payment-service: connection pool exhausted", age: "2m ago", status: "Analyzing…", statusColor: "text-indigo-400" },
  { id: "0046", sev: "HIGH",     color: "text-orange-400", dot: "bg-orange-500", title: "auth-service: elevated 5xx rate (12%)",       age: "8m ago", status: "Identified", statusColor: "text-yellow-400" },
  { id: "0045", sev: "MEDIUM",   color: "text-amber-400", dot: "bg-amber-500", title: "celery-worker: queue backlog > 2000",          age: "14m ago", status: "Monitoring", statusColor: "text-blue-400" },
  { id: "0044", sev: "LOW",      color: "text-blue-400", dot: "bg-blue-500", title: "cdn-edge: cache miss ratio elevated",             age: "32m ago", status: "Resolved", statusColor: "text-green-400" },
];

export default async function HomePage() {
  const health = await getBackendHealth();

  return (
    <main className="flex min-h-screen flex-col bg-[#020913]">

      {/* ── Nav ── */}
      <nav className="relative border-b border-cyan-500/[0.1] bg-[#06101f]">
        <div className="nav-scan-line" />
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 shadow-glow-cyan">
              <Bot className="h-4 w-4 text-cyan-400" />
            </div>
            <span className="text-sm font-semibold tracking-tight text-white">
              AI Ops Copilot
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="text-slate-500 font-mono uppercase tracking-widest">
              API
            </span>
            {health ? <StatusBadge status={health.status} /> : <StatusBadge status="error" />}
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative flex flex-1 items-center overflow-hidden px-6 py-20">
        {/* Gradient blobs */}
        <div className="hero-mesh pointer-events-none absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute -left-40 top-0 h-[600px] w-[600px] rounded-full bg-cyan-500/[0.05] blur-[120px]" />
          <div className="absolute -right-40 bottom-0 h-[500px] w-[500px] rounded-full bg-indigo-500/[0.06] blur-[120px]" />
          <div className="absolute left-1/2 top-1/3 h-[300px] w-[300px] -translate-x-1/2 rounded-full bg-blue-500/[0.04] blur-[80px]" />
        </div>

        <div className="mx-auto w-full max-w-7xl">
          <div className="grid items-center gap-16 lg:grid-cols-2">

            {/* Left — copy */}
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/[0.07] px-4 py-1.5 text-xs font-medium text-cyan-300">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping-slow absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-400" />
                </span>
                AI-Powered Incident Response · Real-Time
              </div>

              <h1 className="text-5xl font-bold leading-[1.1] tracking-tight text-white sm:text-6xl">
                When the pager
                <br />
                fires at{" "}
                <span className="bg-gradient-to-r from-cyan-300 via-cyan-400 to-teal-300 bg-clip-text text-transparent">
                  3 AM,
                </span>
                <br />
                answers are ready.
              </h1>

              <p className="mt-6 max-w-lg text-base leading-relaxed text-slate-400">
                AI Ops Copilot ingests your infrastructure alerts, correlates related
                events into incidents, and delivers AI-generated root-cause analysis
                and remediation steps — right when your on-call team needs them.
              </p>

              <div className="mt-10 flex flex-wrap gap-4">
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 rounded-lg border border-cyan-500/40 bg-cyan-500/15 px-6 py-3 text-sm font-semibold text-cyan-300 shadow-glow-cyan transition hover:bg-cyan-500/25 hover:text-cyan-200"
                >
                  Open Dashboard
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
                </Link>
                <a
                  href="http://localhost:8000/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.04] px-6 py-3 text-sm font-medium text-slate-300 transition hover:bg-white/[0.08] hover:text-white"
                >
                  API Docs
                </a>
              </div>

              {/* Stats strip */}
              <div className="mt-12 flex flex-wrap gap-8">
                {[
                  { value: "< 30s", label: "Mean time to AI analysis" },
                  { value: "80+",   label: "Automated tests" },
                  { value: "5",     label: "Native integrations" },
                ].map((s) => (
                  <div key={s.label}>
                    <p className="text-2xl font-bold tabular-nums text-white">{s.value}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right — mock live feed */}
            <div className="hidden lg:block">
              <div className="relative rounded-xl border border-cyan-500/[0.12] bg-[#06101f] shadow-glow-cyan">
                {/* Panel header */}
                <div className="flex items-center justify-between border-b border-cyan-500/[0.1] px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <Radio className="h-3.5 w-3.5 text-cyan-400" />
                    <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                      Live Incidents
                    </span>
                  </div>
                  <span className="flex items-center gap-1.5 text-[10px] text-green-400">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-green-500" />
                    </span>
                    CONNECTED
                  </span>
                </div>

                {/* Incident rows */}
                <div className="divide-y divide-white/[0.04]">
                  {mockIncidents.map((inc, i) => (
                    <div
                      key={inc.id}
                      className="flex items-start gap-3 px-5 py-3.5"
                      style={{ animationDelay: `${i * 0.1}s` }}
                    >
                      <span className={`mt-1 h-2 w-2 flex-shrink-0 rounded-full ${inc.dot} ${i === 0 ? "animate-pulse" : ""}`} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className={`font-mono text-[10px] font-bold ${inc.color}`}>{inc.sev}</span>
                            <span className="font-mono text-[10px] text-slate-600">INC-{inc.id}</span>
                          </div>
                          <span className={`text-[10px] font-medium ${inc.statusColor}`}>{inc.status}</span>
                        </div>
                        <p className="mt-0.5 truncate text-xs text-slate-300">{inc.title}</p>
                        <p className="mt-0.5 text-[10px] text-slate-600 font-mono">{inc.age}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* AI analysis indicator */}
                <div className="border-t border-cyan-500/[0.08] px-5 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className="relative">
                      <Bot className="h-4 w-4 text-indigo-400" />
                      <span className="absolute -right-0.5 -top-0.5 flex h-2 w-2">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500" />
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      <span className="text-indigo-300 font-medium">AI</span>
                      {" "}analyzing INC-0047 · root cause identified
                    </p>
                  </div>
                </div>

                {/* Decorative corner accent */}
                <div className="pointer-events-none absolute -right-px -top-px h-10 w-10 overflow-hidden rounded-tr-xl">
                  <div className="absolute right-0 top-0 h-full w-px bg-gradient-to-b from-cyan-400/60 to-transparent" />
                  <div className="absolute right-0 top-0 h-px w-full bg-gradient-to-l from-cyan-400/60 to-transparent" />
                </div>
                <div className="pointer-events-none absolute -bottom-px -left-px h-10 w-10 overflow-hidden rounded-bl-xl">
                  <div className="absolute bottom-0 left-0 h-full w-px bg-gradient-to-t from-cyan-400/40 to-transparent" />
                  <div className="absolute bottom-0 left-0 h-px w-full bg-gradient-to-r from-cyan-400/40 to-transparent" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Feature grid ── */}
      <section className="border-t border-cyan-500/[0.06] px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="mb-3 text-center">
            <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-500">
              Platform Capabilities
            </span>
          </div>
          <h2 className="mb-12 text-center text-3xl font-bold tracking-tight text-white">
            Everything your on-call team needs
          </h2>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, description, color, bg, border }) => (
              <div
                key={title}
                className={`group relative rounded-xl border bg-[#081320] p-6 transition-all hover:-translate-y-0.5 ${border} hover:shadow-glow-cyan`}
              >
                <div className={`mb-5 inline-flex h-11 w-11 items-center justify-center rounded-lg border ${border} ${bg}`}>
                  <Icon className={`h-5 w-5 ${color}`} />
                </div>
                <h3 className="mb-2 font-semibold text-white">{title}</h3>
                <p className="text-sm leading-relaxed text-slate-500">{description}</p>
                {/* Corner accent */}
                <div className={`pointer-events-none absolute right-0 top-0 h-8 w-8 overflow-hidden rounded-tr-xl opacity-0 transition-opacity group-hover:opacity-100`}>
                  <div className="absolute right-0 top-0 h-full w-px bg-gradient-to-b from-cyan-400/50 to-transparent" />
                  <div className="absolute right-0 top-0 h-px w-full bg-gradient-to-l from-cyan-400/50 to-transparent" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Service health ── */}
      {health && (
        <section className="border-t border-cyan-500/[0.06] px-6 py-8">
          <div className="mx-auto max-w-7xl">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">
                System Health
              </span>
              <div className="h-px flex-1 bg-white/[0.04]" />
              {Object.entries(health.services).map(([svc, status]) => (
                <div
                  key={svc}
                  className="flex items-center gap-2 rounded-lg border border-white/[0.06] bg-[#081320] px-3 py-1.5 text-xs"
                >
                  <span className="capitalize text-slate-400 font-mono">{svc}</span>
                  <StatusBadge status={status === "ok" ? "ok" : "error"} />
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Footer ── */}
      <footer className="border-t border-cyan-500/[0.06] px-6 py-5">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-3.5 w-3.5 text-cyan-500/50" />
            <span className="text-xs text-slate-600 font-mono">AI Ops Copilot v0.1.0</span>
          </div>
          <span className="text-xs text-slate-700 font-mono">
            Next.js · FastAPI · PostgreSQL · Redis · OpenAI
          </span>
        </div>
      </footer>
    </main>
  );
}
