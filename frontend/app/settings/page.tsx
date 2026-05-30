"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, CheckCircle2, Loader2, Settings as SettingsIcon, ShieldCheck } from "lucide-react";
import { changePassword, errorMessage, logout } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { withAuth } from "@/lib/withAuth";

const RULES = [
  { test: (p: string) => p.length >= 8, label: "At least 8 characters" },
  { test: (p: string) => /[A-Z]/.test(p), label: "One uppercase letter" },
  { test: (p: string) => /[0-9]/.test(p), label: "One number" },
  { test: (p: string) => /[^A-Za-z0-9]/.test(p), label: "One special character" },
];

const labelCls = "mb-1.5 block text-sm font-medium text-[#cbd5e1]";
const inputCls =
  "w-full rounded-lg border border-[#3b4268] bg-[#1e2235] px-3 py-2.5 text-sm text-[#e2e8f0] placeholder:text-[#64748b] outline-none focus:border-[#3b82f6]";

function ChangePasswordForm({ forceMode }: { forceMode: boolean }) {
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);

  const rulesPass = RULES.map((r) => r.test(next));
  const allValid = rulesPass.every(Boolean) && next === confirm && current.length > 0;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (next !== confirm) {
      setError("New password and confirmation do not match.");
      return;
    }
    setBusy(true);
    try {
      await changePassword(current, next);
      setSuccess(true);
      if (forceMode) {
        // First-login flow: password set, continue to the dashboard.
        setTimeout(() => router.replace("/dashboard"), 1200);
      } else {
        // Normal change: tokens were revoked server-side; log out after 3s.
        setTimeout(async () => {
          await logout();
          router.replace("/login");
        }, 3000);
      }
    } catch (err) {
      setError(errorMessage(err, "Could not change password."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-[#2d3748] bg-[#1a1d2e] p-6">
      <h2 className="mb-1 text-lg font-bold text-white">Change Password</h2>
      <p className="mb-4 text-sm text-[#94a3b8]">Choose a strong password you will remember.</p>

      {success && (
        <div className="mb-4 rounded-lg border border-[#22c55e] bg-[#14532d] px-3 py-2 text-sm text-white">
          <CheckCircle2 className="mr-1 inline h-4 w-4" />
          Password changed successfully.{" "}
          {forceMode ? "Redirecting to your dashboard…" : "You will be logged out in a few seconds…"}
        </div>
      )}
      {error && (
        <div className="mb-4 rounded-lg border border-[#7f1d1d] bg-[#2d1515] px-3 py-2 text-sm text-[#ef4444]">
          {error}
        </div>
      )}

      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className={labelCls}>Current Password</label>
          <input type="password" className={inputCls} value={current} onChange={(e) => setCurrent(e.target.value)} placeholder="••••••••" />
        </div>
        <div>
          <label className={labelCls}>New Password</label>
          <input type="password" className={inputCls} value={next} onChange={(e) => setNext(e.target.value)} placeholder="••••••••" />
        </div>
        <div>
          <label className={labelCls}>Confirm New Password</label>
          <input type="password" className={inputCls} value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="••••••••" />
        </div>

        <ul className="grid grid-cols-2 gap-1 text-xs">
          {RULES.map((r, i) => (
            <li key={r.label} className={rulesPass[i] ? "text-[#22c55e]" : "text-[#64748b]"}>
              {rulesPass[i] ? "✓" : "○"} {r.label}
            </li>
          ))}
        </ul>

        <button
          type="submit"
          disabled={!allValid || busy || success}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#3b82f6] text-sm font-semibold text-white transition hover:bg-[#2f6fe0] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" />} Update Password
        </button>
      </form>
    </div>
  );
}

function SettingsInner() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const forceMode = searchParams.get("force_change") === "true";

  // In force mode, render a full-screen overlay that hides all navigation.
  useEffect(() => {
    if (forceMode) document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [forceMode]);

  if (forceMode) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-[#0f1117] px-4 py-10">
        <div className="w-full max-w-md">
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#f59e0b] bg-[#3a2a08] px-4 py-3 text-sm text-[#f59e0b]">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            You must change your password before continuing.
          </div>
          <div className="mb-4 flex items-center gap-2 text-[#94a3b8]">
            <ShieldCheck className="h-5 w-5 text-[#3b82f6]" />
            <span className="text-sm">First-time sign-in — set your own password.</span>
          </div>
          <ChangePasswordForm forceMode />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
        <SettingsIcon className="h-6 w-6 text-[#3b82f6]" /> Account Settings
      </h1>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-[#2d3748] bg-[#1a1d2e] p-6">
          <h2 className="mb-3 text-lg font-bold text-white">Account</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between border-b border-[#2d3748] py-2">
              <span className="text-[#64748b]">Signed in as</span>
              <span className="font-mono text-[#e2e8f0]">{user?.email ?? user?.id ?? "—"}</span>
            </div>
            <div className="flex justify-between border-b border-[#2d3748] py-2">
              <span className="text-[#64748b]">Role</span>
              <span className="text-[#e2e8f0]">{user?.role ?? "—"}</span>
            </div>
            <p className="pt-2 text-xs text-[#64748b]">
              System settings (retention, SMTP, scheduler) are managed via the server .env configuration.
            </p>
          </div>
        </div>

        <ChangePasswordForm forceMode={false} />
      </div>
    </div>
  );
}

function SettingsPage() {
  return (
    <Suspense fallback={null}>
      <SettingsInner />
    </Suspense>
  );
}

export default withAuth(SettingsPage, ["viewer", "admin", "super_admin"]);
