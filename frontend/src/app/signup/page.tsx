"use client";

import { Bot, Activity, Shield, Zap } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiSignup } from "@/lib/api";
import { setAuth } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    orgName: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      const res = await apiSignup(form.email, form.password, form.orgName, form.fullName || undefined);
      setAuth(res.access_token, {
        user_id: res.user_id,
        email: res.email,
        org_id: res.org_id,
        org_name: res.org_name,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "rounded-lg border border-cyan-500/[0.1] bg-[#020913] px-3.5 py-2.5 text-sm text-white placeholder-slate-700 outline-none transition focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20";
  const labelClass =
    "text-[11px] font-semibold uppercase tracking-widest text-slate-500";

  return (
    <div className="flex min-h-screen bg-[#020913]">
      {/* Gradient blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-60 top-0 h-[500px] w-[500px] rounded-full bg-cyan-500/[0.04] blur-[100px]" />
        <div className="absolute -right-60 bottom-0 h-[400px] w-[400px] rounded-full bg-indigo-500/[0.05] blur-[100px]" />
      </div>

      {/* Left branding panel */}
      <div className="relative hidden w-[40%] flex-col justify-between border-r border-cyan-500/[0.08] bg-[#06101f] p-12 lg:flex">
        <div className="nav-scan-line" />
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 shadow-glow-cyan">
            <Bot className="h-5 w-5 text-cyan-400" />
          </div>
          <span className="font-semibold text-white">AI Ops Copilot</span>
        </div>
        <div className="space-y-5">
          <h2 className="text-3xl font-bold leading-tight text-white">
            Your entire team,{" "}
            <span className="bg-gradient-to-r from-cyan-300 to-teal-300 bg-clip-text text-transparent">
              one platform.
            </span>
          </h2>
          <p className="text-sm leading-relaxed text-slate-400">
            Create your organization and start correlating alerts into actionable incidents in minutes.
          </p>
          <div className="space-y-3">
            {[
              { icon: Zap,      text: "Free to get started" },
              { icon: Activity, text: "Live dashboard from day one" },
              { icon: Shield,   text: "Multi-tenant data isolation" },
              { icon: Bot,      text: "AI analysis included" },
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
        <p className="font-mono text-[10px] text-slate-700 uppercase tracking-widest">
          v0.1.0 · Next.js · FastAPI · PostgreSQL
        </p>
      </div>

      {/* Right form panel */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-6 lg:hidden flex flex-col items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 shadow-glow-cyan">
              <Bot className="h-5 w-5 text-cyan-400" />
            </div>
            <h1 className="text-lg font-semibold text-white">AI Ops Copilot</h1>
          </div>

          <div className="mb-7">
            <h2 className="text-2xl font-bold text-white">Create your account</h2>
            <p className="mt-1 text-sm text-slate-500">Set up your organization and get started</p>
          </div>

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

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className={labelClass} htmlFor="orgName">Organization name</label>
                <input id="orgName" type="text" required value={form.orgName} onChange={update("orgName")} placeholder="Acme Corp" className={inputClass} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className={labelClass} htmlFor="fullName">
                  Full name <span className="text-slate-700 normal-case tracking-normal">(optional)</span>
                </label>
                <input id="fullName" type="text" value={form.fullName} onChange={update("fullName")} placeholder="Jane Smith" className={inputClass} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className={labelClass} htmlFor="email">Email</label>
                <input id="email" type="email" autoComplete="email" required value={form.email} onChange={update("email")} placeholder="you@example.com" className={inputClass} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className={labelClass} htmlFor="password">Password</label>
                <input id="password" type="password" autoComplete="new-password" required minLength={6} value={form.password} onChange={update("password")} placeholder="Min. 6 characters" className={inputClass} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className={labelClass} htmlFor="confirmPassword">Confirm password</label>
                <input id="confirmPassword" type="password" autoComplete="new-password" required value={form.confirmPassword} onChange={update("confirmPassword")} placeholder="••••••••" className={inputClass} />
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
                {loading ? "Creating account…" : "Create account →"}
              </button>
            </form>
          </div>

          <p className="mt-5 text-center text-xs text-slate-600">
            Already have an account?{" "}
            <Link href="/login" className="text-cyan-400 transition hover:text-cyan-300">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
