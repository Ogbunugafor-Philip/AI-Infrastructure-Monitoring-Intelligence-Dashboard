"use client";

import { useCallback, useEffect, useState } from "react";
import { BrainCircuit, Loader2, RefreshCw } from "lucide-react";
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
import { matchRecommendation } from "@/lib/commandMatch";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PasswordPromptDialog } from "@/components/PasswordPromptDialog";
import { ActionRequestModal } from "@/components/actions/ActionRequestModal";
import { AIReportDisplay } from "@/components/AIReportDisplay";

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

  const safeCommands: CommandItem[] = catalog && report
    ? (report.recommended_actions ?? [])
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
      }
    }
    setRunResult(`Executed ${ran} of ${safeCommands.length} safe action(s).`);
    return true;
  }

  return (
    <section className="rounded-2xl border border-[#2d3748] bg-[#1a1d2e] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-bold text-white">
          <BrainCircuit className="h-5 w-5 text-[#3b82f6]" /> AI Analysis
        </h2>
        {canGenerate && report && (
          <Button variant="outline" size="sm" onClick={handleGenerate} disabled={generating}>
            {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            {generating ? "Generating…" : "Generate New Report"}
          </Button>
        )}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-8 text-sm text-[#64748b]">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : (
        <AIReportDisplay
          report={report}
          generating={generating}
          onGenerate={canGenerate ? handleGenerate : undefined}
          onExecuteAction={onExecuteRec}
          canExecute={canGenerate}
        />
      )}

      {report && canGenerate && safeCommands.length > 0 && (
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={() => { setRunResult(null); setRunAllOpen(true); }}>
            Run All Safe Actions ({safeCommands.length})
          </Button>
          {runResult && <p className="mt-2 text-xs text-[#22c55e]">{runResult}</p>}
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
