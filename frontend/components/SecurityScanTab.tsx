"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ScanLine,
  Wrench,
  XCircle,
} from "lucide-react";
import {
  type CommandCatalog,
  type CommandItem,
  type ScanCheck,
  type SecurityScan,
  getCommands,
  getLatestSecurityScan,
  runSecurityScan,
} from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { flattenCatalog } from "@/lib/commandMatch";
import { timeAgo } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { ActionRequestModal } from "@/components/actions/ActionRequestModal";

function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

const STATUS_ORDER: Record<ScanCheck["status"], number> = { critical: 0, warning: 1, pass: 2 };

function StatusIcon({ status }: { status: ScanCheck["status"] }) {
  if (status === "pass") return <CheckCircle2 className="h-5 w-5 text-[#22c55e]" />;
  if (status === "warning") return <AlertTriangle className="h-5 w-5 text-[#f59e0b]" />;
  return <XCircle className="h-5 w-5 text-[#ef4444]" />;
}

function ScoreGauge({ score }: { score: number }) {
  const color = scoreColor(score);
  const r = 52;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  return (
    <div className="relative h-32 w-32">
      <svg width="128" height="128" className="-rotate-90">
        <circle cx="64" cy="64" r={r} stroke="#2d3748" strokeWidth="10" fill="none" />
        <circle cx="64" cy="64" r={r} stroke={color} strokeWidth="10" fill="none" strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-extrabold" style={{ color }}>{score}</span>
        <span className="text-xs text-[#64748b]">/ 100</span>
      </div>
    </div>
  );
}

export function SecurityScanTab({
  serverId,
  serverName,
  serverIp,
}: {
  serverId: string;
  serverName: string;
  serverIp: string;
}) {
  const { hasRole } = useAuth();
  const canScan = hasRole("admin", "super_admin");
  const [scan, setScan] = useState<SecurityScan | null>(null);
  const [catalog, setCatalog] = useState<CommandCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fixCmd, setFixCmd] = useState<CommandItem | null>(null);

  const load = useCallback(async () => {
    try {
      setScan(await getLatestSecurityScan(serverId));
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    load();
    getCommands().then(setCatalog).catch(() => setCatalog({ low: [], medium: [], high: [] }));
  }, [load]);

  async function handleScan() {
    setRunning(true);
    setError(null);
    try {
      setScan(await runSecurityScan(serverId));
    } catch {
      setError("Scan failed — verify the server is reachable over SSH.");
    } finally {
      setRunning(false);
    }
  }

  const byKey = useMemo(() => (catalog ? flattenCatalog(catalog) : {}), [catalog]);

  const sortedChecks = useMemo(() => {
    const checks = scan?.scan_results ?? [];
    return [...checks].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]);
  }, [scan]);

  return (
    <div className="space-y-6">
      {/* Scan header */}
      <div className="flex flex-wrap items-center gap-6 rounded-2xl border border-[#2d3748] bg-[#1a1d2e] p-5">
        {scan ? <ScoreGauge score={scan.overall_score} /> : (
          <div className="flex h-32 w-32 items-center justify-center rounded-full border border-dashed border-[#2d3748] text-sm text-[#64748b]">No scan</div>
        )}
        <div className="flex-1 space-y-2">
          <div className="flex flex-wrap gap-3 text-sm">
            <span className="rounded-md bg-[#14532d] px-2.5 py-1 font-medium text-white">{scan?.passed ?? 0} Passed</span>
            <span className="rounded-md bg-[#3a2a08] px-2.5 py-1 font-medium text-[#f59e0b]">{scan?.warnings ?? 0} Warnings</span>
            <span className="rounded-md bg-[#2d1515] px-2.5 py-1 font-medium text-[#ef4444]">{scan?.critical_findings ?? 0} Critical</span>
          </div>
          <p className="text-xs text-[#64748b]">
            {scan ? `Last scanned ${timeAgo(scan.scanned_at)}` : "No scan has been run yet."}
          </p>
          {canScan && (
            <Button onClick={handleScan} disabled={running}>
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanLine className="h-4 w-4" />}
              {running ? "Scanning…" : "Run Security Scan"}
            </Button>
          )}
          {error && <p className="text-xs text-[#ef4444]">{error}</p>}
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="text-sm text-[#64748b]">Loading…</div>
      ) : !scan || sortedChecks.length === 0 ? (
        <EmptyState title="No scan results" description={canScan ? "Run a security scan to see findings." : "No scan available."} icon={<ScanLine className="h-6 w-6" />} />
      ) : (
        <div className="space-y-3">
          {sortedChecks.map((check, i) => {
            const fix = check.fix_command_key ? byKey[check.fix_command_key] : null;
            return (
              <div key={i} className="rounded-xl border border-[#2d3748] bg-[#1a1d2e] p-4">
                <div className="flex items-start gap-3">
                  <StatusIcon status={check.status} />
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-white">{check.check_name}</p>
                    <p className="mt-1 text-sm text-[#e2e8f0]">{check.finding}</p>
                    <p className="mt-1 text-xs text-[#94a3b8]">{check.recommendation}</p>
                  </div>
                  <div className="shrink-0">
                    {fix && canScan ? (
                      <Button size="sm" onClick={() => setFixCmd(fix)}>
                        <Wrench className="h-3.5 w-3.5" /> Fix It
                      </Button>
                    ) : check.status !== "pass" ? (
                      <span className="rounded-md border border-[#2d3748] px-2 py-1 text-xs text-[#94a3b8]">Manual Fix Required</span>
                    ) : null}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {fixCmd && (
        <ActionRequestModal
          open={!!fixCmd}
          onOpenChange={(o) => !o && setFixCmd(null)}
          serverId={serverId}
          serverName={serverName}
          serverIp={serverIp}
          command={fixCmd}
          requesterEmail="you"
        />
      )}
    </div>
  );
}
