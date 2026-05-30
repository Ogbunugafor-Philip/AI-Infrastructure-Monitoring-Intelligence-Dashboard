"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowDownUp,
  ArrowLeft,
  BrainCircuit,
  Clock,
  Cpu,
  Network,
  RefreshCw,
  Search,
  Terminal,
} from "lucide-react";
import {
  type Metric,
  type MetricHistory,
  type Server,
  getLatestMetric,
  getMetricHistory,
  getServer,
  refreshMetrics,
} from "@/lib/api";
import { withAuth } from "@/lib/withAuth";
import { timeAgo, formatDateTime } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Gauge } from "@/components/ui/gauge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MultiServerChart } from "@/components/dashboard/MultiServerChart";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ChartSkeleton, Skeleton } from "@/components/Skeletons";

const STATUS_BADGE: Record<Server["status"], "online" | "offline" | "warning"> = {
  online: "online",
  offline: "offline",
  warning: "warning",
};

function buildSeries(history: MetricHistory | null, field: "cpu_usage" | "ram_usage" | "disk_usage") {
  const rows = (history?.points ?? []).map((p) => ({ time: p.collected_at, v: p[field] }));
  return rows;
}

function ServerDetailPage({ params }: { params: Promise<{ server_id: string }> }) {
  const { server_id } = use(params);
  const [server, setServer] = useState<Server | null>(null);
  const [metric, setMetric] = useState<Metric | null>(null);
  const [history, setHistory] = useState<MetricHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [procSearch, setProcSearch] = useState("");
  const [logSearch, setLogSearch] = useState("");
  const [sortKey, setSortKey] = useState<"name" | "pid" | "cpu" | "memory">("cpu");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const load = useCallback(async () => {
    const [srv, met, hist] = await Promise.all([
      getServer(server_id),
      getLatestMetric(server_id),
      getMetricHistory(server_id, 24).catch(() => null),
    ]);
    setServer(srv);
    setMetric(met);
    setHistory(hist);
  }, [server_id]);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, [load]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const res = await refreshMetrics(server_id);
      if (res.metric) setMetric(res.metric);
      await load();
    } finally {
      setRefreshing(false);
    }
  }

  const processes = useMemo(() => {
    const list = (metric?.running_processes ?? []).filter((p) =>
      p.name?.toLowerCase().includes(procSearch.toLowerCase()),
    );
    return [...list].sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      const cmp = typeof av === "number" && typeof bv === "number"
        ? av - bv
        : String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [metric, procSearch, sortKey, sortDir]);

  const ports = metric?.open_ports ?? [];

  // Derived activity log lines from the latest metric (real log streaming is a
  // future enhancement; these are generated from collected metrics).
  const logs = useMemo(() => {
    if (!metric) return [] as { level: string; text: string }[];
    const lines: { level: string; text: string }[] = [];
    const ts = formatDateTime(metric.collected_at);
    lines.push({ level: "INFO", text: `${ts}  metrics collected (cpu ${metric.cpu_usage ?? "?"}%, ram ${metric.ram_usage ?? "?"}%, disk ${metric.disk_usage ?? "?"}%)` });
    if ((metric.cpu_usage ?? 0) >= 80) lines.push({ level: "WARN", text: `${ts}  high CPU utilisation: ${metric.cpu_usage}%` });
    if ((metric.ram_usage ?? 0) >= 80) lines.push({ level: "WARN", text: `${ts}  high memory utilisation: ${metric.ram_usage}%` });
    if ((metric.disk_usage ?? 0) >= 90) lines.push({ level: "ERROR", text: `${ts}  disk nearly full: ${metric.disk_usage}%` });
    (metric.running_processes ?? []).slice(0, 5).forEach((p) =>
      lines.push({ level: "INFO", text: `${ts}  proc ${p.name} pid=${p.pid} cpu=${p.cpu}% mem=${p.memory}%` }),
    );
    return lines.filter((l) => l.text.toLowerCase().includes(logSearch.toLowerCase()));
  }, [metric, logSearch]);

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-72" />
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}
        </div>
        <ChartSkeleton />
      </div>
    );
  }

  if (!server) {
    return (
      <div className="p-6">
        <EmptyState title="Server not found" description="It may have been deleted." />
        <div className="mt-4">
          <Link href="/dashboard"><Button variant="outline"><ArrowLeft className="h-4 w-4" /> Back to Dashboard</Button></Link>
        </div>
      </div>
    );
  }

  function toggleSort(key: typeof sortKey) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("desc"); }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/dashboard" className="mb-2 inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200">
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <span className={`h-3 w-3 rounded-full ${server.status === "online" ? "bg-emerald-500" : server.status === "warning" ? "bg-amber-500" : "bg-red-500"}`} />
            <h1 className="text-2xl font-semibold">{server.name}</h1>
            <Badge variant={STATUS_BADGE[server.status]}>{server.status}</Badge>
            {server.ssh_key_only_mode && <Badge variant="accent">Key-only</Badge>}
          </div>
          <p className="mt-1 font-mono text-sm text-slate-400">
            {server.ip_address}:{server.ssh_port} · {server.ssh_username} · {server.ssh_auth_method} auth
          </p>
          <p className="text-xs text-slate-500">Last updated {timeAgo(metric?.collected_at)}</p>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>

      {/* Metric cards */}
      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Card><CardContent className="flex justify-center p-4"><Gauge value={metric?.cpu_usage ?? null} label="CPU" /></CardContent></Card>
        <Card><CardContent className="flex justify-center p-4"><Gauge value={metric?.ram_usage ?? null} label="RAM" /></CardContent></Card>
        <Card><CardContent className="flex justify-center p-4"><Gauge value={metric?.disk_usage ?? null} label="Disk" /></CardContent></Card>
        <StatTile icon={<Clock className="h-5 w-5" />} label="Uptime" value={metric?.uptime ?? "—"} />
        <StatTile icon={<Cpu className="h-5 w-5" />} label="Processes" value={String((metric?.running_processes ?? []).length)} />
        <StatTile icon={<Network className="h-5 w-5" />} label="Open Ports" value={String((metric?.open_ports ?? []).length)} />
      </div>

      {/* Charts */}
      <div className="grid gap-5 lg:grid-cols-3">
        <ErrorBoundary><MultiServerChart title="CPU — 24h" rows={buildSeries(history, "cpu_usage")} series={[{ key: "v", name: "CPU" }]} /></ErrorBoundary>
        <ErrorBoundary><MultiServerChart title="RAM — 24h" rows={buildSeries(history, "ram_usage")} series={[{ key: "v", name: "RAM" }]} /></ErrorBoundary>
        <ErrorBoundary><MultiServerChart title="Disk — 24h" rows={buildSeries(history, "disk_usage")} series={[{ key: "v", name: "Disk" }]} /></ErrorBoundary>
      </div>

      {/* Processes + Ports */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Running Processes</h2>
            <div className="relative w-56">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <Input value={procSearch} onChange={(e) => setProcSearch(e.target.value)} placeholder="Filter processes…" className="pl-8" />
            </div>
          </div>
          {processes.length === 0 ? (
            <EmptyState title="No process data" description="Refresh to collect process info." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  {(["name", "pid", "cpu", "memory"] as const).map((k) => (
                    <TableHead key={k}>
                      <button className="inline-flex items-center gap-1" onClick={() => toggleSort(k)}>
                        {k === "name" ? "Process" : k === "pid" ? "PID" : k === "cpu" ? "CPU%" : "Mem%"}
                        <ArrowDownUp className="h-3 w-3 opacity-50" />
                      </button>
                    </TableHead>
                  ))}
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {processes.map((p, i) => (
                  <TableRow key={`${p.pid}-${i}`}>
                    <TableCell className="font-mono">{p.name}</TableCell>
                    <TableCell>{p.pid}</TableCell>
                    <TableCell>{p.cpu ?? "—"}</TableCell>
                    <TableCell>{p.memory ?? "—"}</TableCell>
                    <TableCell><Badge variant="default">{p.status}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold">Open Ports</h2>
          {ports.length === 0 ? (
            <EmptyState title="No open ports data" description="Refresh to collect listening ports." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Port</TableHead>
                  <TableHead>Protocol</TableHead>
                  <TableHead>Service</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Process</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ports.map((p, i) => (
                  <TableRow key={`${p.port}-${i}`}>
                    <TableCell className="font-mono">{p.port}</TableCell>
                    <TableCell>{p.protocol}</TableCell>
                    <TableCell>{p.service || "—"}</TableCell>
                    <TableCell><Badge variant="online">{p.state}</Badge></TableCell>
                    <TableCell className="font-mono text-xs">{p.process || "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      </div>

      {/* Logs + AI analysis */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-semibold"><Terminal className="h-5 w-5 text-slate-400" /> Recent Logs</h2>
            <div className="relative w-48">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <Input value={logSearch} onChange={(e) => setLogSearch(e.target.value)} placeholder="Filter logs…" className="pl-8" />
            </div>
          </div>
          {logs.length === 0 ? (
            <EmptyState title="No log entries" description="Logs are derived from collected metrics." />
          ) : (
            <div className="max-h-72 space-y-1 overflow-y-auto rounded-lg bg-slate-950 p-3 font-mono text-xs">
              {logs.map((l, i) => (
                <div key={i} className={l.level === "ERROR" ? "text-red-400" : l.level === "WARN" ? "text-amber-400" : "text-slate-300"}>
                  <span className="mr-2 font-semibold">[{l.level}]</span>{l.text}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-semibold"><BrainCircuit className="h-5 w-5 text-indigo-400" /> AI Analysis</h2>
            <Button variant="outline" size="sm" disabled title="AI report generation arrives in a later phase">
              <RefreshCw className="h-3.5 w-3.5" /> Refresh AI Analysis
            </Button>
          </div>
          <EmptyState
            title="No AI analysis yet"
            description="AI-generated risk reports and recommendations will appear here once generated."
            icon={<BrainCircuit className="h-6 w-6" />}
          />
        </section>
      </div>
    </div>
  );
}

function StatTile({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center gap-1 p-4 text-center">
        <div className="text-slate-400">{icon}</div>
        <p className="truncate text-sm font-semibold text-slate-100" title={value}>{value}</p>
        <span className="text-xs text-slate-400">{label}</span>
      </CardContent>
    </Card>
  );
}

export default withAuth(ServerDetailPage, ["viewer", "admin", "super_admin"]);
