"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { type SecurityAlert, getSecurityAlerts } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/EmptyState";
import { TableSkeleton } from "@/components/Skeletons";

const SEVERITY_DOT: Record<SecurityAlert["severity"], string> = {
  high: "bg-red-500",
  medium: "bg-orange-500",
  low: "bg-yellow-500",
};

/** Right-rail panel showing the latest security alerts. Admin+ only. */
export function SecurityAlertsPanel({ limit = 10 }: { limit?: number }) {
  const [alerts, setAlerts] = useState<SecurityAlert[] | null>(null);

  useEffect(() => {
    let active = true;
    const fetchAlerts = () =>
      getSecurityAlerts(limit)
        .then((data) => active && setAlerts(data))
        .catch(() => active && setAlerts([]));
    fetchAlerts();
    const id = setInterval(fetchAlerts, 60_000); // auto-refresh every 60s
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [limit]);

  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-4 flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-red-400" />
        <h3 className="text-sm font-semibold text-slate-200">Security Alerts</h3>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto">
        {alerts === null ? (
          <TableSkeleton rows={5} />
        ) : alerts.length === 0 ? (
          <EmptyState title="No recent alerts" description="All clear." icon={<ShieldAlert className="h-6 w-6" />} />
        ) : (
          alerts.map((a) => (
            <div key={a.id} className="flex items-start gap-3 rounded-lg border border-slate-800 p-3">
              <span className="relative mt-1 flex h-2.5 w-2.5 shrink-0">
                {a.severity === "high" && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                )}
                <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", SEVERITY_DOT[a.severity])} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-slate-200">{a.event_type}</span>
                  <span className="shrink-0 text-xs text-slate-500">{timeAgo(a.created_at)}</span>
                </div>
                <p className="mt-0.5 truncate text-xs text-slate-400">
                  {a.event_description ?? "—"}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      <Link
        href="/security-alerts"
        className="mt-4 block text-center text-xs font-medium text-indigo-400 hover:text-indigo-300"
      >
        View All Alerts →
      </Link>
    </div>
  );
}
