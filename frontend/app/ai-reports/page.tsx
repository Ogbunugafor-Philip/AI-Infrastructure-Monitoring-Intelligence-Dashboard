"use client";

import { useEffect, useState } from "react";
import { BrainCircuit, ChevronDown, ChevronRight } from "lucide-react";
import {
  type AiReport,
  type ServerStatusItem,
  getLatestAiReport,
  getServersStatus,
} from "@/lib/api";
import { withAuth } from "@/lib/withAuth";
import { riskColor } from "@/lib/gauge-color";
import { timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { CardGridSkeleton } from "@/components/Skeletons";
import { EmptyState } from "@/components/EmptyState";
import { AIReportPanel } from "@/components/AIReportPanel";

function RiskBadge({ score, level }: { score: number | null; level: string | null }) {
  if (score === null) {
    return <span className="rounded-md bg-slate-800 px-2 py-0.5 text-xs text-slate-400">No report</span>;
  }
  const color = riskColor(score);
  return (
    <span
      className="rounded-md px-2 py-0.5 text-xs font-semibold"
      style={{ background: `${color}22`, color }}
    >
      {score}/10 {level ? `· ${level}` : ""}
    </span>
  );
}

function AiReportsPage() {
  const [servers, setServers] = useState<ServerStatusItem[] | null>(null);
  const [reports, setReports] = useState<Record<string, AiReport | null>>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    getServersStatus()
      .then(async (list) => {
        setServers(list);
        const entries = await Promise.all(
          list.map(async (s) => [s.id, await getLatestAiReport(s.id).catch(() => null)] as const),
        );
        setReports(Object.fromEntries(entries));
      })
      .catch(() => setServers([]));
  }, []);

  return (
    <div className="space-y-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-semibold">
        <BrainCircuit className="h-6 w-6 text-indigo-400" /> AI Reports
      </h1>
      <p className="text-sm text-slate-400">
        AI-generated infrastructure health reports per server. Click a server to view the full report.
      </p>

      {servers === null ? (
        <CardGridSkeleton count={3} />
      ) : servers.length === 0 ? (
        <EmptyState title="No servers registered" description="Register a server to generate AI reports." icon={<BrainCircuit className="h-6 w-6" />} />
      ) : (
        <div className="space-y-3">
          {servers.map((s) => {
            const report = reports[s.id];
            const isOpen = expanded === s.id;
            return (
              <Card key={s.id}>
                <button
                  className="flex w-full items-center justify-between p-4 text-left"
                  onClick={() => setExpanded(isOpen ? null : s.id)}
                >
                  <div className="flex items-center gap-3">
                    {isOpen ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
                    <div>
                      <p className="font-semibold">{s.name}</p>
                      <p className="font-mono text-xs text-slate-400">{s.ip_address}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {report && (
                      <span className="hidden text-xs text-slate-500 sm:inline">
                        {timeAgo(report.generated_at)}
                      </span>
                    )}
                    <RiskBadge score={report?.risk_score ?? null} level={report?.risk_level ?? null} />
                  </div>
                </button>
                <div className={cn("overflow-hidden transition-all", isOpen ? "block" : "hidden")}>
                  <CardContent className="pt-0">
                    {isOpen && <AIReportPanel serverId={s.id} />}
                  </CardContent>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default withAuth(AiReportsPage, ["viewer", "admin", "super_admin"]);
