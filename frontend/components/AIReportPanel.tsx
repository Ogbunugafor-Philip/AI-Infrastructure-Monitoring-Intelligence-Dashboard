"use client";

import { useCallback, useEffect, useState } from "react";
import { BrainCircuit, CheckCircle2, Loader2, RefreshCw, ShieldAlert, Zap } from "lucide-react";
import {
  type AiReport,
  generateAiReport,
  getLatestAiReport,
  waitForTask,
} from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { riskColor } from "@/lib/gauge-color";
import { formatDateTime } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { Skeleton } from "@/components/Skeletons";

function List({ items, icon }: { items: string[] | null; icon?: React.ReactNode }) {
  if (!items || items.length === 0) return <p className="text-sm text-slate-500">None.</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((it, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
          <span className="mt-0.5 shrink-0 text-slate-500">{icon ?? <CheckCircle2 className="h-4 w-4" />}</span>
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}

export function AIReportPanel({ serverId }: { serverId: string }) {
  const { hasRole } = useAuth();
  const canGenerate = hasRole("admin", "super_admin");
  const [report, setReport] = useState<AiReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    try {
      setReport(await getLatestAiReport(serverId));
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleGenerate() {
    setGenerating(true);
    try {
      const { task_id } = await generateAiReport(serverId);
      await waitForTask(serverId, task_id, { timeoutMs: 120000 });
      await load();
    } finally {
      setGenerating(false);
    }
  }

  const score = report?.risk_score ?? null;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <BrainCircuit className="h-5 w-5 text-indigo-400" /> AI Analysis
        </h2>
        {canGenerate && (
          <Button variant="outline" size="sm" onClick={handleGenerate} disabled={generating}>
            {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            {generating ? "Generating…" : "Generate New Report"}
          </Button>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-32" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : !report ? (
        <EmptyState
          title="No AI analysis yet"
          description={canGenerate ? "Generate a report to see AI insights." : "No report has been generated yet."}
          icon={<BrainCircuit className="h-6 w-6" />}
          action={
            canGenerate ? (
              <Button size="sm" onClick={handleGenerate} disabled={generating}>
                {generating && <Loader2 className="h-4 w-4 animate-spin" />} Generate Report
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-5">
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-5xl font-bold" style={{ color: riskColor(score ?? 5) }}>
                {score ?? "—"}
              </div>
              <div className="text-xs text-slate-400">Risk Score /10</div>
            </div>
            <div>
              <div
                className="inline-block rounded-md px-2 py-0.5 text-xs font-semibold"
                style={{ background: `${riskColor(score ?? 5)}22`, color: riskColor(score ?? 5) }}
              >
                {(report.risk_level ?? "unknown").toUpperCase()}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Generated {formatDateTime(report.generated_at)}
              </p>
            </div>
          </div>

          <div>
            <h3 className="mb-1 text-sm font-semibold text-slate-200">Summary</h3>
            <p className="text-sm leading-relaxed text-slate-300">{report.summary}</p>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-200">Key Findings</h3>
              <List items={report.key_findings} icon={<Zap className="h-4 w-4 text-amber-400" />} />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-200">Recommended Actions</h3>
              <List items={report.recommended_actions} />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-200">Security Observations</h3>
              <List items={report.security_observations} icon={<ShieldAlert className="h-4 w-4 text-red-400" />} />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-200">Performance Observations</h3>
              <List items={report.performance_observations} icon={<Zap className="h-4 w-4 text-indigo-400" />} />
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
