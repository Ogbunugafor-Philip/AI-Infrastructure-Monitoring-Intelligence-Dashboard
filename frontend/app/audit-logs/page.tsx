"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Download, ScrollText, XCircle } from "lucide-react";
import {
  type AuditLogPage,
  type AuditLogQuery,
  downloadAuditCsv,
  getAuditLogs,
} from "@/lib/api";
import { withAuth } from "@/lib/withAuth";
import { formatDateTime } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TableSkeleton } from "@/components/Skeletons";
import { EmptyState } from "@/components/EmptyState";

const EVENT_TYPES = [
  "", "login", "login_failed", "logout", "token_refresh", "session_expired",
  "intrusion_detected", "credential_reveal", "password_reverify",
  "server_registered", "server_updated", "server_deleted",
  "server_key_only_toggled", "ssh_connection_attempt", "ip_whitelist_denied",
];

function eventBadgeVariant(t: string): "default" | "online" | "warning" | "accent" {
  if (t.includes("intrusion") || t.includes("denied") || t === "login_failed") return "warning";
  if (t.includes("registered") || t === "login") return "online";
  if (t.includes("reveal") || t.includes("deleted")) return "accent";
  return "default";
}

const PAGE_SIZE = 50;

function AuditLogsPage() {
  const [data, setData] = useState<AuditLogPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<AuditLogQuery>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getAuditLogs({ ...filters, page, page_size: PAGE_SIZE });
      setData(result);
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    load();
  }, [load]);

  function updateFilter(key: keyof AuditLogQuery, value: string) {
    setPage(1);
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
  }

  async function handleExport() {
    setExporting(true);
    try {
      await downloadAuditCsv(filters);
    } finally {
      setExporting(false);
    }
  }

  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <ScrollText className="h-6 w-6 text-indigo-400" /> Audit Logs
        </h1>
        <Button onClick={handleExport} disabled={exporting}>
          <Download className="h-4 w-4" /> {exporting ? "Exporting…" : "Export to CSV"}
        </Button>
      </div>

      {/* Filters */}
      <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <label className="mb-1 block text-xs text-slate-400">From</label>
          <Input type="date" onChange={(e) => updateFilter("date_from", e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">To</label>
          <Input type="date" onChange={(e) => updateFilter("date_to", e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Event type</label>
          <Select onChange={(e) => updateFilter("event_type", e.target.value)}>
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>{t || "All events"}</option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">User ID</label>
          <Input placeholder="user uuid" onChange={(e) => updateFilter("user_id", e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Server ID</label>
          <Input placeholder="server uuid" onChange={(e) => updateFilter("server_id", e.target.value)} />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <TableSkeleton rows={10} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState title="No audit entries" description="No events match the current filters." icon={<ScrollText className="h-6 w-6" />} />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Event</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Target Server</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>IP</TableHead>
                <TableHead>Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="whitespace-nowrap text-xs">{formatDateTime(r.created_at)}</TableCell>
                  <TableCell><Badge variant={eventBadgeVariant(r.event_type)}>{r.event_type}</Badge></TableCell>
                  <TableCell className="font-mono text-xs">{r.user_id ? r.user_id.slice(0, 8) : "—"}</TableCell>
                  <TableCell className="font-mono text-xs">{r.target_server_id ? r.target_server_id.slice(0, 8) : "—"}</TableCell>
                  <TableCell className="max-w-xs truncate text-xs" title={r.event_description ?? ""}>{r.event_description ?? "—"}</TableCell>
                  <TableCell className="font-mono text-xs">{r.ip_address ?? "—"}</TableCell>
                  <TableCell>
                    {r.success ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-400" />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>
              Page {data.page} of {totalPages} · {data.total} entries
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default withAuth(AuditLogsPage, ["super_admin"]);
