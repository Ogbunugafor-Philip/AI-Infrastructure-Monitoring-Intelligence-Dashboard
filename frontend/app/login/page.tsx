"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Cookies from "js-cookie";
import { Lock, Mail, ShieldCheck, Loader2 } from "lucide-react";
import { login } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionExpired = searchParams.get("reason") === "session_expired";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await login(email, password);
      // Short-lived access token; refresh token kept for silent renewal.
      Cookies.set("access_token", tokens.access_token, {
        secure: true,
        sameSite: "strict",
        expires: tokens.expires_in / 86400,
      });
      Cookies.set("refresh_token", tokens.refresh_token, {
        secure: true,
        sameSite: "strict",
      });
      router.replace("/dashboard");
    } catch (err: unknown) {
      // Never surface server internals; show a generic, safe message.
      const status =
        typeof err === "object" && err !== null && "response" in err
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;
      setError(
        status === 429
          ? "Too many attempts. Please wait a moment and try again."
          : "Invalid email or password.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/60 p-8 shadow-xl backdrop-blur">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-semibold">AI Infrastructure Monitoring</h1>
          <p className="mt-1 text-sm text-slate-400">Sign in to your dashboard</p>
        </div>

        {sessionExpired && (
          <div className="mb-4 rounded-lg border border-amber-700/50 bg-amber-900/20 px-3 py-2 text-sm text-amber-300">
            Your session expired due to inactivity. Please sign in again.
          </div>
        )}
        {error && (
          <div className="mb-4 rounded-lg border border-red-700/50 bg-red-900/20 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm text-slate-300">Email</span>
            <div className="flex items-center rounded-lg border border-slate-700 bg-slate-950 px-3">
              <Mail className="h-4 w-4 text-slate-500" />
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-transparent px-2 py-2.5 text-sm outline-none"
                placeholder="you@example.com"
              />
            </div>
          </label>

          <label className="block">
            <span className="mb-1 block text-sm text-slate-300">Password</span>
            <div className="flex items-center rounded-lg border border-slate-700 bg-slate-950 px-3">
              <Lock className="h-4 w-4 text-slate-500" />
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-transparent px-2 py-2.5 text-sm outline-none"
                placeholder="••••••••"
              />
            </div>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-500">
          Protected by rate limiting, intrusion detection &amp; audit logging.
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
