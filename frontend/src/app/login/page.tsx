"use client";

import { Bot } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiLogin } from "@/lib/api";
import { setAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
    <div className="flex min-h-screen items-center justify-center bg-[#0a0a15] px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20">
            <Bot className="h-5 w-5 text-indigo-400" />
          </div>
          <h1 className="text-lg font-semibold text-white">AI Ops Copilot</h1>
          <p className="text-sm text-slate-500">Sign in to your account</p>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-400" htmlFor="email">
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
                className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-sm text-white placeholder-slate-600 outline-none ring-indigo-500/50 transition focus:border-indigo-500/50 focus:ring-1"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-400" htmlFor="password">
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
                className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-sm text-white placeholder-slate-600 outline-none ring-indigo-500/50 transition focus:border-indigo-500/50 focus:ring-1"
              />
            </div>

            {error && (
              <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          {/* Demo credentials hint */}
          <div className="mt-4 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 text-xs text-slate-500">
            <span className="text-slate-400">Demo:</span>{" "}
            <span className="font-mono">demo@example.com</span> /{" "}
            <span className="font-mono">demo1234</span>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-slate-600">
          No account?{" "}
          <Link href="/signup" className="text-indigo-400 hover:text-indigo-300">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
