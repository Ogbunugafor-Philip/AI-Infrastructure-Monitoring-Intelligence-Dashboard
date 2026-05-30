"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity } from "lucide-react";
import { type ServerStatusItem, getServersStatus } from "@/lib/api";
import { withAuth } from "@/lib/withAuth";
import { timeAgo } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CardGridSkeleton } from "@/components/Skeletons";
import { EmptyState } from "@/components/EmptyState";

function MetricsPage() {
  const [servers, setServers] = useState<ServerStatusItem[] | null>(null);

  useEffect(() => {
    getServersStatus().then(setServers).catch(() => setServers([]));
  }, []);

  return (
    <div className="space-y-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-semibold">
        <Activity className="h-6 w-6 text-indigo-400" /> Metrics
      </h1>
      <p className="text-sm text-slate-400">Select a server to view its detailed metrics and charts.</p>

      {servers === null ? (
        <CardGridSkeleton count={3} />
      ) : servers.length === 0 ? (
        <EmptyState title="No servers to display" description="Register a server to collect metrics." icon={<Activity className="h-6 w-6" />} />
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {servers.map((s) => (
            <Link key={s.id} href={`/servers/${s.id}`}>
              <Card className="transition-colors hover:border-indigo-700">
                <CardContent className="space-y-3 p-5">
                  <div className="flex items-center justify-between">
                    <p className="truncate font-semibold">{s.name}</p>
                    <Badge variant={s.status === "online" ? "online" : s.status === "warning" ? "warning" : "offline"}>{s.status}</Badge>
                  </div>
                  <p className="font-mono text-xs text-slate-400">{s.ip_address}</p>
                  <div className="space-y-2">
                    <Bar label="CPU" v={s.cpu_usage} />
                    <Bar label="RAM" v={s.ram_usage} />
                    <Bar label="Disk" v={s.disk_usage} />
                  </div>
                  <p className="text-xs text-slate-500">Updated {timeAgo(s.last_updated)}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Bar({ label, v }: { label: string; v: number | null }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-9 shrink-0 text-xs text-slate-500">{label}</span>
      <Progress value={v ?? 0} showLabel />
    </div>
  );
}

export default withAuth(MetricsPage, ["viewer", "admin", "super_admin"]);
