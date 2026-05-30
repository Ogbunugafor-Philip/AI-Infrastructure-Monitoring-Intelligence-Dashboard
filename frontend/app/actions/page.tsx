"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Loader2, PlayCircle, Send, Terminal } from "lucide-react";
import {
  type ActionHistoryPage,
  type ActionRecord,
  type CommandCatalog,
  type CommandItem,
  type DryRunResult,
  type ServerStatusItem,
  dryRunCommand,
  errorMessage,
  getActionHistory,
  getCommands,
  getServersStatus,
} from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { withAuth } from "@/lib/withAuth";
import { formatDateTime } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TableSkeleton, CardGridSkeleton } from "@/components/Skeletons";
import { EmptyState } from "@/components/EmptyState";
import { Alert } from "@/components/ui/alert";
import { SecondConfirmPanel } from "@/components/actions/SecondConfirmPanel";
import { DryRunModal } from "@/components/actions/DryRunModal";
import { ActionRequestModal } from "@/components/actions/ActionRequestModal";

const RISK_VARIANT: Record<string, "online" | "warning" | "default"> = {
  low: "online",
  medium: "warning",
  high: "default",
};
const STATUS_VARIANT: Record<string, "online" | "warning" | "accent" | "default"> = {
  completed: "online",
  approved: "accent",
  executing: "accent",
  pending: "warning",
  awaiting_second_confirmation: "warning",
  cancelled: "default",
  expired: "default",
};

function CommandCard({
  command,
  servers,
  onDryRun,
  onRequest,
}: {
  command: CommandItem;
  servers: ServerStatusItem[];
  onDryRun: (serverId: string) => Promise<void>;
  onRequest: (serverId: string) => void;
}) {
  const [serverId, setServerId] = useState(servers[0]?.id ?? "");
  const [dryRunning, setDryRunning] = useState(false);

  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-semibold">{command.command_key}</p>
            <p className="text-xs text-slate-400">{command.description}</p>
          </div>
          <Badge variant={RISK_VARIANT[command.risk_level]}>{command.risk_level}</Badge>
        </div>
        <pre className="overflow-x-auto rounded-lg bg-slate-950 p-2 text-xs text-emerald-300">{command.command_string}</pre>
        <Select value={serverId} onChange={(e) => setServerId(e.target.value)}>
          {servers.length === 0 && <option value="">No servers</option>}
          {servers.map((s) => (
            <option key={s.id} value={s.id}>{s.name} ({s.ip_address})</option>
          ))}
        </Select>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            className="flex-1"
            disabled={!serverId || dryRunning}
            onClick={async () => {
              setDryRunning(true);
              try {
                await onDryRun(serverId);
              } finally {
                setDryRunning(false);
              }
            }}
          >
            {dryRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PlayCircle className="h-3.5 w-3.5" />}
            Dry Run
          </Button>
          <Button size="sm" className="flex-1" disabled={!serverId} onClick={() => onRequest(serverId)}>
            <Send className="h-3.5 w-3.5" /> Request
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ActionsPage() {
  const { user } = useAuth();
  const [catalog, setCatalog] = useState<CommandCatalog | null>(null);
  const [servers, setServers] = useState<ServerStatusItem[]>([]);
  const [tab, setTab] = useState<"low" | "medium" | "high">("low");
  const [history, setHistory] = useState<ActionHistoryPage | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [filters, setFilters] = useState<{ status?: string; risk_level?: string; server_id?: string }>({});
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [dryRunResult, setDryRunResult] = useState<DryRunResult | null>(null);
  const [dryRunServerName, setDryRunServerName] = useState("");
  const [dryRunOpen, setDryRunOpen] = useState(false);
  const [reqModal, setReqModal] = useState<{ command: CommandItem; server: ServerStatusItem } | null>(null);
  const [outputModal, setOutputModal] = useState<ActionRecord | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await getActionHistory({ ...filters, page: historyPage, page_size: 25 }));
    } catch (e) {
      setError(errorMessage(e, "Could not load action history."));
    }
  }, [filters, historyPage]);

  useEffect(() => {
    getCommands().then(setCatalog).catch(() => setCatalog({ low: [], medium: [], high: [] }));
    getServersStatus().then(setServers).catch(() => setServers([]));
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  async function handleDryRun(command: CommandItem, serverId: string) {
    setError(null);
    const server = servers.find((s) => s.id === serverId);
    try {
      const result = await dryRunCommand(serverId, command.command_key);
      setDryRunResult(result);
      setDryRunServerName(server?.name ?? "");
      setDryRunOpen(true);
    } catch (e) {
      setError(errorMessage(e, "Dry run failed."));
    }
  }

  function handleRequest(command: CommandItem, serverId: string) {
    const server = servers.find((s) => s.id === serverId);
    if (server) setReqModal({ command, server });
  }

  const commands = catalog?.[tab] ?? [];

  return (
    <div className="space-y-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-semibold">
        <Terminal className="h-6 w-6 text-indigo-400" /> Actions
      </h1>

      {error && <Alert variant="destructive">{error}</Alert>}

      {/* Second confirmation panel (admin/super who are not the requester) */}
      <SecondConfirmPanel onChange={loadHistory} />

      {/* Execute Action */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Execute Action</h2>
        <div className="inline-flex rounded-lg border border-slate-700 p-1">
          {(["low", "medium", "high"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-md px-4 py-1.5 text-sm capitalize ${tab === t ? "bg-indigo-600 text-white" : "text-slate-300"}`}
            >
              {t} Risk
            </button>
          ))}
        </div>

        {tab === "high" && (
          <Alert variant="destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>High risk commands require dual confirmation from a second Admin/Super Admin and enforce a 60-second time lock before execution.</span>
          </Alert>
        )}

        {catalog === null ? (
          <CardGridSkeleton count={6} />
        ) : commands.length === 0 ? (
          <EmptyState title="No commands in this category" />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {commands.map((c) => (
              <CommandCard
                key={c.command_key}
                command={c}
                servers={servers}
                onDryRun={(sid) => handleDryRun(c, sid)}
                onRequest={(sid) => handleRequest(c, sid)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Action history */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Action History</h2>
        <div className="flex flex-wrap gap-3">
          <div className="w-44">
            <Select value={filters.status ?? ""} onChange={(e) => { setHistoryPage(1); setFilters((f) => ({ ...f, status: e.target.value || undefined })); }}>
              <option value="">All statuses</option>
              {["pending", "awaiting_second_confirmation", "approved", "executing", "completed", "cancelled", "expired"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </Select>
          </div>
          <div className="w-40">
            <Select value={filters.risk_level ?? ""} onChange={(e) => { setHistoryPage(1); setFilters((f) => ({ ...f, risk_level: e.target.value || undefined })); }}>
              <option value="">All risk levels</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </Select>
          </div>
          <div className="w-56">
            <Select value={filters.server_id ?? ""} onChange={(e) => { setHistoryPage(1); setFilters((f) => ({ ...f, server_id: e.target.value || undefined })); }}>
              <option value="">All servers</option>
              {servers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </Select>
          </div>
        </div>

        {history === null ? (
          <TableSkeleton rows={6} />
        ) : history.items.length === 0 ? (
          <EmptyState title="No actions yet" description="Requested and executed actions appear here." />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Server</TableHead>
                  <TableHead>Command</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Requested by</TableHead>
                  <TableHead>Confirmed by</TableHead>
                  <TableHead>Output</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.items.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="whitespace-nowrap text-xs">{formatDateTime(a.created_at)}</TableCell>
                    <TableCell className="text-xs">{a.server_name}<br /><span className="font-mono text-slate-500">{a.server_ip}</span></TableCell>
                    <TableCell className="font-mono text-xs">{a.command_key}</TableCell>
                    <TableCell><Badge variant={RISK_VARIANT[a.risk_level]}>{a.risk_level}</Badge></TableCell>
                    <TableCell><Badge variant={STATUS_VARIANT[a.status] ?? "default"}>{a.status}</Badge></TableCell>
                    <TableCell className="font-mono text-xs">{a.requested_by_user_id?.slice(0, 8) ?? "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{a.confirmed_by_user_id?.slice(0, 8) ?? "—"}</TableCell>
                    <TableCell>
                      {a.execution_output ? (
                        <Button variant="ghost" size="sm" onClick={() => setOutputModal(a)}>View</Button>
                      ) : <span className="text-xs text-slate-500">—</span>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="flex items-center justify-between text-sm text-slate-400">
              <span>Page {history.page} of {history.total_pages} · {history.total} actions</span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={historyPage <= 1} onClick={() => setHistoryPage((p) => p - 1)}>Previous</Button>
                <Button variant="outline" size="sm" disabled={historyPage >= history.total_pages} onClick={() => setHistoryPage((p) => p + 1)}>Next</Button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Modals */}
      <DryRunModal
        open={dryRunOpen}
        onOpenChange={setDryRunOpen}
        result={dryRunResult}
        serverName={dryRunServerName}
      />
      {reqModal && (
        <ActionRequestModal
          open={!!reqModal}
          onOpenChange={(o) => { if (!o) { setReqModal(null); loadHistory(); } }}
          serverId={reqModal.server.id}
          serverName={reqModal.server.name}
          serverIp={reqModal.server.ip_address}
          command={reqModal.command}
          requesterEmail={user?.email ?? user?.id ?? "you"}
          onDone={loadHistory}
        />
      )}
      <Dialog open={!!outputModal} onOpenChange={(o) => !o && setOutputModal(null)}>
        <DialogHeader>
          <DialogTitle>Execution Output — {outputModal?.command_key}</DialogTitle>
        </DialogHeader>
        <pre className="max-h-80 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-200">{outputModal?.execution_output}</pre>
        <DialogFooter><Button variant="outline" onClick={() => setOutputModal(null)}>Close</Button></DialogFooter>
      </Dialog>
    </div>
  );
}

export default withAuth(ActionsPage, ["admin", "super_admin"]);
