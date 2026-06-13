"use client";

import { Bot, Shield, Zap, Activity } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiLogin } from "@/lib/api";
import { setAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).has("expired")) {
      setNotice("Your session expired. Please sign in again.");
    }
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiLogin(email, password);
      setAuth(res.access_token, {
        user_id: res.user_id,
        email: res.email,
        org_id: res.org_id,
        org_name: res.org_name,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-[#020913]">
      {/* Gradient blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-60 top-0 h-[500px] w-[500px] rounded-full bg-cyan-500/[0.04] blur-[100px]" />
        <div className="absolute -right-60 bottom-0 h-[400px] w-[400px] rounded-full bg-indigo-500/[0.05] blur-[100px]" />
      </div>

      {/* Left panel — branding */}
      <div className="relative hidden w-[45%] flex-col justify-between border-r border-cyan-500/[0.08] bg-[#06101f] p-12 lg:flex">
        <div className="nav-scan-line" />

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 shadow-glow-cyan">
            <Bot className="h-5 w-5 text-cyan-400" />
          </div>
          <span className="font-semibold text-white">AI Ops Copilot</span>
        </div>

        {/* Middle — value props */}
        <div className="space-y-6">
          <h2 className="text-3xl font-bold leading-tight text-white">
            Resolve incidents
            <br />
            <span className="bg-gradient-to-r from-cyan-300 to-teal-300 bg-clip-text text-transparent">
              before they escalate.
            </span>
          </h2>
          <p className="text-sm leading-relaxed text-slate-400">
            AI-powered root-cause analysis delivered to your on-call team in seconds, not hours.
          </p>
          <div className="space-y-3">
            {[
              { icon: Zap,      text: "Automatic alert correlation into incidents" },
              { icon: Bot,      text: "GPT-4o-mini root-cause analysis" },
              { icon: Activity, text: "Real-time WebSocket dashboard" },
              { icon: Shield,   text: "Multi-tenant org isolation" },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3 text-sm text-slate-400">
                <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg border border-cyan-500/15 bg-cyan-500/[0.07]">
                  <Icon className="h-3.5 w-3.5 text-cyan-400" />
                </div>
                {text}
              </div>
            ))}
          </div>
        </div>

        {/* Bottom */}
        <p className="font-mono text-[10px] text-slate-700 uppercase tracking-widest">
          v0.1.0 · Next.js · FastAPI · PostgreSQL
        </p>

        {/* Decorative corner */}
        <div className="pointer-events-none absolute right-0 top-0 h-16 w-16 overflow-hidden">
          <div className="absolute right-0 top-0 h-full w-px bg-gradient-to-b from-cyan-400/40 to-transparent" />
        </div>
        <div className="pointer-events-none absolute bottom-0 right-0 h-16 w-16 overflow-hidden">
          <div className="absolute bottom-0 right-0 h-full w-px bg-gradient-to-t from-cyan-400/20 to-transparent" />
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="mb-8 flex flex-col items-center gap-2 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 shadow-glow-cyan">
              <Bot className="h-5 w-5 text-cyan-400" />
            </div>
            <h1 className="text-lg font-semibold text-white">AI Ops Copilot</h1>
          </div>

          <div className="mb-8 lg:block">
            <h2 className="text-2xl font-bold text-white">Welcome back</h2>
            <p className="mt-1 text-sm text-slate-500">Sign in to your operations dashboard</p>
          </div>

          {/* Card */}
          <div className="relative rounded-xl border border-cyan-500/[0.12] bg-[#06101f] p-7 shadow-glow-cyan">
            {/* Corner accents */}
            <div className="pointer-events-none absolute -left-px -top-px h-8 w-8 overflow-hidden rounded-tl-xl">
              <div className="absolute left-0 top-0 h-full w-px bg-gradient-to-b from-cyan-400/50 to-transparent" />
              <div className="absolute left-0 top-0 h-px w-full bg-gradient-to-r from-cyan-400/50 to-transparent" />
            </div>
            <div className="pointer-events-none absolute -bottom-px -right-px h-8 w-8 overflow-hidden rounded-br-xl">
              <div className="absolute bottom-0 right-0 h-full w-px bg-gradient-to-t from-cyan-400/30 to-transparent" />
              <div className="absolute bottom-0 right-0 h-px w-full bg-gradient-to-l from-cyan-400/30 to-transparent" />
            </div>

            {notice && (
              <div className="mb-4 rounded-lg border border-amber-500/25 bg-amber-500/[0.08] px-3.5 py-2.5 text-xs text-amber-300" role="status">
                {notice}
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-semibold uppercase tracking-widest text-slate-500" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="rounded-lg border border-cyan-500/[0.1] bg-[#020913] px-3.5 py-2.5 text-sm text-white placeholder-slate-700 outline-none transition focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-semibold uppercase tracking-widest text-slate-500" htmlFor="password">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="rounded-lg border border-cyan-500/[0.1] bg-[#020913] px-3.5 py-2.5 text-sm text-white placeholder-slate-700 outline-none transition focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20"
                />
              </div>

              {error && (
                <div className="rounded-lg border border-red-500/25 bg-red-500/[0.08] px-3.5 py-2.5 text-xs text-red-400">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="mt-1 rounded-lg border border-cyan-500/30 bg-cyan-500/15 px-4 py-2.5 text-sm font-semibold text-cyan-300 shadow-glow-cyan transition hover:bg-cyan-500/25 hover:text-cyan-200 disabled:opacity-50"
              >
                {loading ? "Signing in…" : "Sign in →"}
              </button>
            </form>

            {/* Demo hint */}
            <div className="mt-5 rounded-lg border border-cyan-500/[0.08] bg-cyan-500/[0.03] px-3.5 py-3 text-xs text-slate-500">
              <span className="font-semibold text-slate-400">Demo account:</span>{" "}
              <span className="font-mono text-slate-300">demo@example.com</span>
              <span className="text-slate-600"> / </span>
              <span className="font-mono text-slate-300">demo1234</span>
            </div>
          </div>

          <p className="mt-5 text-center text-xs text-slate-600">
            No account?{" "}
            <Link href="/signup" className="text-cyan-400 transition hover:text-cyan-300">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
