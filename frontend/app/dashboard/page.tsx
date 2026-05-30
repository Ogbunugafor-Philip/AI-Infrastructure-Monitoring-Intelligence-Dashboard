"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Server as ServerIcon,
  WifiOff,
} from "lucide-react";
import {
  type Metric,
  type Overview,
  type ServerStatusItem,
  getMetricHistory,
  getOverview,
  getServersStatus,
  refreshMetrics,
} from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { withAuth } from "@/lib/withAuth";
import { timeAgo } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { CardGridSkeleton, Skeleton } from "@/components/Skeletons";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { MultiServerChart, type SeriesMeta } from "@/components/dashboard/MultiServerChart";
import { SecurityAlertsPanel } from "@/components/dashboard/SecurityAlertsPanel";

const STATUS_BADGE: Record<ServerStatusItem["status"], "online" | "offline" | "warning"> = {
  online: "online",
  offline: "offline",
  warning: "warning",
};

function StatCard({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  accent: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className="mt-1 text-3xl font-bold text-slate-100">{value}</p>
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${accent}`}>
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}

function DashboardPage() {
  const { hasRole } = useAuth();
  const canSeeAlerts = hasRole("admin", "super_admin");

  const [overview, setOverview] = useState<Overview | null>(null);
  const [servers, setServers] = useState<ServerStatusItem[] | null>(null);
  const [chartRows, setChartRows] = useState<{ cpu: Record<string, number | string | null>[]; ram: Record<string, number | string | null>[] }>({ cpu: [], ram: [] });
  const [chartSeries, setChartSeries] = useState<SeriesMeta[]>([]);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const loadCore = useCallback(async (silent = false) => {
    try {
      const [ov, st] = await Promise.all([getOverview(), getServersStatus()]);
      setOverview(ov);
      setServers(st);
    } catch {
      if (!silent) {
        setOverview((o) => o);
        setServers((s) => s ?? []);
      }
    }
  }, []);

  const loadCharts = useCallback(async (list: ServerStatusItem[]) => {
    if (list.length === 0) {
      setChartRows({ cpu: [], ram: [] });
      setChartSeries([]);
      return;
    }
    const histories = await Promise.all(
      list.map((s) => getMetricHistory(s.id, 24).catch(() => null)),
    );
    const cpu: Record<string, number | string | null>[] = [];
    const ram: Record<string, number | string | null>[] = [];
    list.forEach((s, i) => {
      const h = histories[i];
      h?.points.forEach((p) => {
        cpu.push({ time: p.collected_at, [s.id]: p.cpu_usage });
        ram.push({ time: p.collected_at, [s.id]: p.ram_usage });
      });
    });
    cpu.sort((a, b) => String(a.time).localeCompare(String(b.time)));
    ram.sort((a, b) => String(a.time).localeCompare(String(b.time)));
    setChartRows({ cpu, ram });
    setChartSeries(list.map((s) => ({ key: s.id, name: s.name })));
  }, []);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    if (servers) loadCharts(servers);
  }, [servers, loadCharts]);

  // Silent auto-refresh of the whole grid + overview every 30s.
  useEffect(() => {
    const id = setInterval(() => loadCore(true), 30_000);
    return () => clearInterval(id);
  }, [loadCore]);

  async function handleRefresh(server: ServerStatusItem) {
    setRefreshingId(server.id);
    try {
      const res = await refreshMetrics(server.id);
      const m: Metric | null = res.metric;
      if (m) {
        setServers((prev) =>
          (prev ?? []).map((s) =>
            s.id === server.id
              ? {
                  ...s,
                  cpu_usage: m.cpu_usage,
                  ram_usage: m.ram_usage,
                  disk_usage: m.disk_usage,
                  uptime: m.uptime,
                  last_updated: m.collected_at,
                  status: (m.cpu_usage ?? 0) >= 80 || (m.ram_usage ?? 0) >= 80 ? "warning" : "online",
                }
              : s,
          ),
        );
      }
      loadCore(true);
    } finally {
      setRefreshingId(null);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 p-6 xl:grid-cols-[1fr_340px]">
      <div className="min-w-0 space-y-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>

        {/* Overview cards */}
        {overview === null ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Servers" value={overview.total_servers} accent="bg-indigo-600/20 text-indigo-400" icon={<ServerIcon className="h-5 w-5" />} />
            <StatCard label="Online" value={overview.servers_online} accent="bg-emerald-600/20 text-emerald-400" icon={<CheckCircle2 className="h-5 w-5" />} />
            <StatCard label="Offline" value={overview.servers_offline} accent="bg-red-600/20 text-red-400" icon={<WifiOff className="h-5 w-5" />} />
            <StatCard label="Warning" value={overview.servers_warning} accent="bg-amber-600/20 text-amber-400" icon={<AlertTriangle className="h-5 w-5" />} />
          </div>
        )}

        {/* Server status grid */}
        <section>
          <h2 className="mb-3 text-lg font-semibold">Servers</h2>
          {servers === null ? (
            <CardGridSkeleton count={3} />
          ) : servers.length === 0 ? (
            <EmptyState
              title="No servers registered"
              description="Register a server to start monitoring."
              icon={<ServerIcon className="h-6 w-6" />}
              action={
                <Link href="/servers/register">
                  <Button variant="secondary" size="sm">Register Server</Button>
                </Link>
              }
            />
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {servers.map((s) => (
                <Card key={s.id} className="flex flex-col">
                  <CardContent className="space-y-3 p-5">
                    <div className="flex items-start justify-between">
                      <div className="min-w-0">
                        <p className="truncate font-semibold">{s.name}</p>
                        <p className="font-mono text-xs text-slate-400">{s.ip_address}:{s.ssh_port}</p>
                      </div>
                      <Badge variant={STATUS_BADGE[s.status]}>{s.status}</Badge>
                    </div>
                    <div className="space-y-2">
                      <MiniBar label="CPU" value={s.cpu_usage} />
                      <MiniBar label="RAM" value={s.ram_usage} />
                      <MiniBar label="Disk" value={s.disk_usage} />
                    </div>
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>{s.uptime ?? "uptime n/a"}</span>
                      <span>Updated {timeAgo(s.last_updated)}</span>
                    </div>
                    <div className="flex gap-2 pt-1">
                      <Link href={`/servers/${s.id}`} className="flex-1">
                        <Button variant="secondary" size="sm" className="w-full">View Details</Button>
                      </Link>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRefresh(s)}
                        disabled={refreshingId === s.id}
                      >
                        <RefreshCw className={`h-3.5 w-3.5 ${refreshingId === s.id ? "animate-spin" : ""}`} />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </section>

        {/* Metrics charts */}
        <section className="grid gap-5 lg:grid-cols-2">
          <ErrorBoundary fallbackTitle="CPU chart failed to render.">
            <MultiServerChart title="CPU Usage — last 24h" rows={chartRows.cpu} series={chartSeries} />
          </ErrorBoundary>
          <ErrorBoundary fallbackTitle="RAM chart failed to render.">
            <MultiServerChart title="RAM Usage — last 24h" rows={chartRows.ram} series={chartSeries} />
          </ErrorBoundary>
        </section>
      </div>

      {/* Right rail: security alerts (admin+) */}
      {canSeeAlerts && (
        <div className="xl:sticky xl:top-6 xl:h-[calc(100vh-3rem)]">
          <ErrorBoundary fallbackTitle="Security panel failed to render.">
            <SecurityAlertsPanel limit={10} />
          </ErrorBoundary>
        </div>
      )}
    </div>
  );
}

function MiniBar({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-9 shrink-0 text-xs text-slate-500">{label}</span>
      <Progress value={value ?? 0} showLabel />
    </div>
  );
}

export default withAuth(DashboardPage, ["viewer", "admin", "super_admin"]);
