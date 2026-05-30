"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Cookies from "js-cookie";
import { Eye, EyeOff, Loader2, Lock, Mail, ShieldCheck } from "lucide-react";
import { login } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionExpired = searchParams.get("reason") === "session_expired";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await login(email, password);
      Cookies.set("access_token", tokens.access_token, {
        secure: true,
        sameSite: "strict",
        expires: tokens.expires_in / 86400,
      });
      Cookies.set("refresh_token", tokens.refresh_token, { secure: true, sameSite: "strict" });
      // First-login forced password change.
      if (tokens.force_password_change) {
        router.replace("/settings?force_change=true");
      } else {
        router.replace("/dashboard");
      }
    } catch (err: unknown) {
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

  const inputClass =
    "w-full bg-transparent px-2 py-2.5 text-sm text-[#e2e8f0] placeholder:text-[#64748b] outline-none";
  const inputWrap =
    "flex items-center rounded-lg border border-[#3b4268] bg-[#1e2235] px-3 focus-within:border-[#3b82f6]";

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0f1117] px-4">
      <div className="w-full max-w-md rounded-xl border border-[#2d3748] bg-[#1a1d2e] p-10 shadow-xl">
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-[#3b82f6]/15 text-[#3b82f6]">
            <ShieldCheck className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-bold text-white">AI Infrastructure Monitor</h1>
          <p className="mt-1 text-sm text-[#94a3b8]">Secure Server Monitoring Dashboard</p>
        </div>

        {sessionExpired && (
          <div className="mb-4 rounded-lg border border-[#7f1d1d] bg-[#2d1515] px-3 py-2 text-sm text-[#f59e0b]">
            Your session expired due to inactivity. Please sign in again.
          </div>
        )}
        {error && (
          <div className="mb-4 rounded-lg border border-[#7f1d1d] bg-[#2d1515] px-3 py-2 text-sm text-[#ef4444]">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-[#cbd5e1]">Email</span>
            <div className={inputWrap}>
              <Mail className="h-4 w-4 text-[#64748b]" />
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
                placeholder="you@example.com"
              />
            </div>
          </label>

          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-[#cbd5e1]">Password</span>
            <div className={inputWrap}>
              <Lock className="h-4 w-4 text-[#64748b]" />
              <input
                type={showPassword ? "text" : "password"}
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="text-[#64748b] hover:text-[#94a3b8]"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#3b82f6] text-sm font-semibold text-white transition hover:bg-[#2f6fe0] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-[#64748b]">
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
