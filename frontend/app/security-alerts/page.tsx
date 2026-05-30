"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { type SecurityAlert, type Severity, getSecurityAlerts } from "@/lib/api";
import { withAuth } from "@/lib/withAuth";
import { formatDateTime, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/Skeletons";
import { EmptyState } from "@/components/EmptyState";

const SEVERITY_COLOR: Record<Severity, string> = {
  high: "bg-red-500",
  medium: "bg-orange-500",
  low: "bg-yellow-500",
};
const SEVERITY_BADGE: Record<Severity, "warning" | "accent" | "default"> = {
  high: "warning",
  medium: "accent",
  low: "default",
};
const SEVERITY_RANK: Record<Severity, number> = { high: 3, medium: 2, low: 1 };

function SecurityAlertsPage() {
  const [alerts, setAlerts] = useState<SecurityAlert[] | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [eventFilter, setEventFilter] = useState<string>("");

  const load = useCallback(async () => {
    try {
      setAlerts(await getSecurityAlerts(100));
    } catch {
      setAlerts([]);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30_000); // auto-refresh every 30s
    return () => clearInterval(id);
  }, [load]);

  const eventTypes = useMemo(
    () => Array.from(new Set((alerts ?? []).map((a) => a.event_type))),
    [alerts],
  );

  const filtered = useMemo(() => {
    let list = alerts ?? [];
    if (severityFilter) list = list.filter((a) => a.severity === severityFilter);
    if (eventFilter) list = list.filter((a) => a.event_type === eventFilter);
    // High severity first, then most recent.
    return [...list].sort((a, b) => {
      if (SEVERITY_RANK[a.severity] !== SEVERITY_RANK[b.severity])
        return SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity];
      return b.created_at.localeCompare(a.created_at);
    });
  }, [alerts, severityFilter, eventFilter]);

  return (
    <div className="space-y-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-semibold">
        <ShieldAlert className="h-6 w-6 text-red-400" /> Security Alerts
      </h1>

      <div className="flex flex-wrap gap-3">
        <div className="w-48">
          <label className="mb-1 block text-xs text-slate-400">Severity</label>
          <Select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
            <option value="">All severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </Select>
        </div>
        <div className="w-56">
          <label className="mb-1 block text-xs text-slate-400">Event type</label>
          <Select value={eventFilter} onChange={(e) => setEventFilter(e.target.value)}>
            <option value="">All events</option>
            {eventTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </Select>
        </div>
      </div>

      {alerts === null ? (
        <TableSkeleton rows={8} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No security alerts" description="Nothing matches the current filters." icon={<ShieldAlert className="h-6 w-6" />} />
      ) : (
        <div className="relative space-y-4 border-l border-slate-800 pl-6">
          {filtered.map((a) => (
            <div key={a.id} className="relative">
              <span className="absolute -left-[1.95rem] top-1.5 flex h-3 w-3">
                {a.severity === "high" && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                )}
                <span className={cn("relative inline-flex h-3 w-3 rounded-full", SEVERITY_COLOR[a.severity])} />
              </span>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={SEVERITY_BADGE[a.severity]}>{a.severity.toUpperCase()}</Badge>
                  <span className="font-medium text-slate-200">{a.event_type}</span>
                  <span className="ml-auto text-xs text-slate-500" title={formatDateTime(a.created_at)}>
                    {timeAgo(a.created_at)}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-300">{a.event_description ?? "—"}</p>
                <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
                  <span>IP: <span className="font-mono">{a.ip_address ?? "—"}</span></span>
                  <span>User: <span className="font-mono">{a.user_id ? a.user_id.slice(0, 8) : "—"}</span></span>
                  <span>Server: <span className="font-mono">{a.target_server_id ? a.target_server_id.slice(0, 8) : "—"}</span></span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default withAuth(SecurityAlertsPage, ["admin", "super_admin"]);
