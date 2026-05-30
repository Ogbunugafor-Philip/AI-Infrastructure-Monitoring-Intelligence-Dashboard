"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  BrainCircuit,
  Loader2,
  PlayCircle,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import {
  type AiReport,
  type CommandCatalog,
  type CommandItem,
  executeAction,
  generateAiReport,
  getCommands,
  getLatestAiReport,
  requestAction,
  verifyActionPassword,
  waitForTask,
} from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { riskColor } from "@/lib/gauge-color";
import { findingBulletColor, matchRecommendation } from "@/lib/commandMatch";
import { formatDateTime } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { Skeleton } from "@/components/Skeletons";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PasswordPromptDialog } from "@/components/PasswordPromptDialog";
import { ActionRequestModal } from "@/components/actions/ActionRequestModal";

function riskLabel(level: string | null, score: number | null): string {
  if (level) return level.toUpperCase();
  if (score === null) return "UNKNOWN";
  return score >= 7 ? "CRITICAL" : score >= 4 ? "WARNING" : "HEALTHY";
}

function Heading({ icon, children }: { icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <h3 className="mb-2 flex items-center gap-2 text-base font-bold text-white">
      {icon}
      {children}
    </h3>
  );
}

export function AIReportPanel({
  serverId,
  serverName = "",
  serverIp = "",
}: {
  serverId: string;
  serverName?: string;
  serverIp?: string;
}) {
  const { hasRole } = useAuth();
  const canGenerate = hasRole("admin", "super_admin");
  const [report, setReport] = useState<AiReport | null>(null);
  const [catalog, setCatalog] = useState<CommandCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  // Execute-related modal state
  const [execCmd, setExecCmd] = useState<CommandItem | null>(null);
  const [manualText, setManualText] = useState<string | null>(null);
  const [runAllOpen, setRunAllOpen] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setReport(await getLatestAiReport(serverId));
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    load();
    getCommands().then(setCatalog).catch(() => setCatalog({ low: [], medium: [], high: [] }));
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

  function onExecuteRec(recText: string) {
    const match = catalog ? matchRecommendation(recText, catalog) : null;
    if (match) setExecCmd(match);
    else setManualText(recText);
  }

  // Low-risk recommendations that map to a whitelisted command.
  const recs: string[] = report?.recommended_actions ?? [];
  const safeCommands: CommandItem[] = catalog
    ? recs
        .map((r) => matchRecommendation(r, catalog))
        .filter((c): c is CommandItem => !!c && c.risk_level === "low")
    : [];

  async function runAllSafe(password: string): Promise<true | string> {
    let ran = 0;
    for (const cmd of safeCommands) {
      try {
        const action = await requestAction(serverId, cmd.command_key);
        await verifyActionPassword(action.id, password);
        await executeAction(action.id);
        ran += 1;
      } catch (err) {
        if (typeof err === "object" && err && "response" in err) {
          const st = (err as { response?: { status?: number } }).response?.status;
          if (st === 403) return "Password verification failed.";
        }
        // skip this one, continue
      }
    }
    setRunResult(`Executed ${ran} of ${safeCommands.length} safe action(s).`);
    return true;
  }

  const score = report?.risk_score ?? null;
  const color = riskColor(score ?? 5);

  return (
    <section className="rounded-2xl border border-[#2d3748] bg-[#1a1d2e] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-bold text-white">
          <BrainCircuit className="h-5 w-5 text-[#3b82f6]" /> AI Analysis
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
          <Skeleton className="h-24 w-40" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : !report ? (
        <EmptyState
          title="No AI analysis yet"
          description={canGenerate ? "Generate a report to see AI insights." : "No report has been generated yet."}
          icon={<BrainCircuit className="h-6 w-6" />}
          action={canGenerate ? <Button size="sm" onClick={handleGenerate} disabled={generating}>{generating && <Loader2 className="h-4 w-4 animate-spin" />} Generate Report</Button> : undefined}
        />
      ) : (
        <div className="space-y-6">
          {/* RISK SCORE */}
          <div className="flex flex-col items-center rounded-xl border border-[#2d3748] bg-[#131625] p-5">
            <div className="text-6xl font-extrabold" style={{ color }}>{score ?? "—"}</div>
            <div className="mt-1 text-sm font-bold tracking-wide" style={{ color }}>
              {riskLabel(report.risk_level, score)}
            </div>
            <div className="mt-3 h-2.5 w-full max-w-xs overflow-hidden rounded-full bg-[#2d3748]">
              <div className="h-full rounded-full" style={{ width: `${((score ?? 0) / 10) * 100}%`, background: color }} />
            </div>
            <div className="mt-1 text-xs text-[#64748b]">Risk score {score ?? "—"} / 10 · generated {formatDateTime(report.generated_at)}</div>
          </div>

          {/* SUMMARY */}
          <div>
            <Heading>Summary</Heading>
            <p className="text-sm text-[#e2e8f0]" style={{ lineHeight: 1.6 }}>{report.summary}</p>
          </div>

          {/* KEY FINDINGS */}
          {report.key_findings && report.key_findings.length > 0 && (
            <div>
              <Heading>Key Findings</Heading>
              <ul className="space-y-2">
                {report.key_findings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-[#e2e8f0]">
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: findingBulletColor(f) }} />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* SECURITY OBSERVATIONS */}
          {report.security_observations && report.security_observations.length > 0 && (
            <div>
              <Heading icon={<ShieldAlert className="h-4 w-4 text-[#ef4444]" />}>Security Observations</Heading>
              <ul className="space-y-2">
                {report.security_observations.map((o, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-[#e2e8f0]">
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" style={{ color: findingBulletColor(o) === "#22c55e" ? "#f59e0b" : findingBulletColor(o) }} />
                    <span>{o}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* PERFORMANCE */}
          {report.performance_observations && report.performance_observations.length > 0 && (
            <div>
              <Heading icon={<Activity className="h-4 w-4 text-[#3b82f6]" />}>Performance</Heading>
              <ul className="space-y-2">
                {report.performance_observations.map((o, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-[#e2e8f0]">
                    <Activity className="mt-0.5 h-4 w-4 shrink-0 text-[#3b82f6]" />
                    <span>{o}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* RECOMMENDED ACTIONS */}
          {recs.length > 0 && (
            <div>
              <Heading>Recommended Actions</Heading>
              <div className="space-y-2.5">
                {recs.map((rec, i) => {
                  const match = catalog ? matchRecommendation(rec, catalog) : null;
                  return (
                    <div key={i} className="flex items-center gap-3 rounded-lg border border-[#2d3748] bg-[#131625] p-3">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#3b82f6]/15 text-sm font-bold text-[#3b82f6]">{i + 1}</span>
                      <span className="flex-1 text-sm text-[#e2e8f0]">{rec}</span>
                      {canGenerate && (
                        <Button size="sm" variant={match ? "default" : "outline"} onClick={() => onExecuteRec(rec)}>
                          <PlayCircle className="h-3.5 w-3.5" /> Execute
                        </Button>
                      )}
                    </div>
                  );
                })}
              </div>
              {canGenerate && safeCommands.length > 0 && (
                <Button className="mt-3" variant="secondary" size="sm" onClick={() => { setRunResult(null); setRunAllOpen(true); }}>
                  Run All Safe Actions ({safeCommands.length})
                </Button>
              )}
              {runResult && <p className="mt-2 text-xs text-[#22c55e]">{runResult}</p>}
            </div>
          )}
        </div>
      )}

      {/* Execute a single recommendation via the Phase-5 action flow */}
      {execCmd && (
        <ActionRequestModal
          open={!!execCmd}
          onOpenChange={(o) => !o && setExecCmd(null)}
          serverId={serverId}
          serverName={serverName}
          serverIp={serverIp}
          command={execCmd}
          requesterEmail="you"
        />
      )}

      {/* Manual execution required */}
      <Dialog open={manualText !== null} onOpenChange={(o) => !o && setManualText(null)}>
        <DialogHeader>
          <DialogTitle>Manual Action Required</DialogTitle>
          <DialogDescription>
            This recommendation has no matching whitelisted command and must be performed manually.
          </DialogDescription>
        </DialogHeader>
        <pre className="whitespace-pre-wrap rounded-lg bg-[#131625] p-3 text-sm text-[#e2e8f0]">{manualText}</pre>
        <DialogFooter>
          <Button variant="outline" onClick={() => setManualText(null)}>Close</Button>
        </DialogFooter>
      </Dialog>

      {/* Run all safe actions: one password, sequential execution */}
      <PasswordPromptDialog
        open={runAllOpen}
        onOpenChange={setRunAllOpen}
        title="Run All Safe Actions"
        description={`Enter your password to run ${safeCommands.length} low-risk action(s) in sequence.`}
        onConfirm={runAllSafe}
      />
    </section>
  );
}
