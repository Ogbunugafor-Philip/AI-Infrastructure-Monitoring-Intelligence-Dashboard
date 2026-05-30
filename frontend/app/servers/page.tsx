"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Circle,
  KeyRound,
  Loader2,
  Lock,
  Pencil,
  PlugZap,
  Plus,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import {
  type Server,
  deleteServer,
  errorMessage,
  listServers,
  testConnection,
  toggleKeyOnly,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { withAuth } from "@/lib/withAuth";

const statusVariant: Record<Server["status"], "online" | "offline" | "warning"> = {
  online: "online",
  offline: "offline",
  warning: "warning",
};

function ServersPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [deleteTarget, setDeleteTarget] = useState<Server | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setServers(await listServers());
    } catch (err) {
      setError(errorMessage(err, "Could not load servers."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleTest(server: Server) {
    setBusyId(server.id);
    try {
      const result = await testConnection({ server_id: server.id });
      setTestResults((prev) => ({ ...prev, [server.id]: result }));
    } catch (err) {
      setTestResults((prev) => ({
        ...prev,
        [server.id]: { success: false, message: errorMessage(err, "Test failed.") },
      }));
    } finally {
      setBusyId(null);
    }
  }

  async function handleToggle(server: Server) {
    setBusyId(server.id);
    try {
      const updated = await toggleKeyOnly(server.id);
      setServers((prev) => prev.map((s) => (s.id === server.id ? updated : s)));
    } catch (err) {
      setError(errorMessage(err, "Could not toggle key-only mode."));
    } finally {
      setBusyId(null);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteServer(deleteTarget.id);
      setServers((prev) => prev.filter((s) => s.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      setError(errorMessage(err, "Could not delete server."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <ShieldCheck className="h-6 w-6 text-indigo-400" /> Registered Servers
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Manage monitored servers. Credentials are encrypted and never displayed here.
          </p>
        </div>
        <Link href="/servers/register">
          <Button>
            <Plus className="h-4 w-4" /> Register Server
          </Button>
        </Link>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          {error}
        </Alert>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading servers…
        </div>
      ) : servers.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <ShieldCheck className="h-10 w-10 text-slate-600" />
            <p className="text-slate-400">No servers registered yet.</p>
            <Link href="/servers/register">
              <Button variant="secondary">
                <Plus className="h-4 w-4" /> Register your first server
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {servers.map((server) => {
            const result = testResults[server.id];
            const busy = busyId === server.id;
            return (
              <Card key={server.id} className="flex flex-col">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="truncate">{server.name}</CardTitle>
                    <Badge variant={statusVariant[server.status]}>
                      <Circle className="h-2 w-2 fill-current" />
                      {server.status}
                    </Badge>
                  </div>
                  <p className="font-mono text-sm text-slate-400">
                    {server.ip_address}:{server.ssh_port}
                  </p>
                </CardHeader>
                <CardContent className="flex-1 space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-slate-300">
                    {server.ssh_auth_method === "key" ? (
                      <KeyRound className="h-4 w-4 text-slate-500" />
                    ) : (
                      <Lock className="h-4 w-4 text-slate-500" />
                    )}
                    <span>
                      {server.ssh_username} · {server.ssh_auth_method} auth
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {server.ssh_key_only_mode && (
                      <Badge variant="accent">
                        <KeyRound className="h-3 w-3" /> Key-only
                      </Badge>
                    )}
                    {server.allowed_ip_whitelist && (
                      <Badge variant="default">IP whitelist set</Badge>
                    )}
                  </div>
                  {result && (
                    <Alert variant={result.success ? "success" : "destructive"} className="text-xs">
                      {result.message}
                    </Alert>
                  )}
                </CardContent>
                <CardFooter className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleTest(server)}
                    disabled={busy}
                  >
                    {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PlugZap className="h-3.5 w-3.5" />}
                    Test
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleToggle(server)} disabled={busy}>
                    <KeyRound className="h-3.5 w-3.5" />
                    {server.ssh_key_only_mode ? "Disable key-only" : "Key-only"}
                  </Button>
                  <Link href={`/servers/${server.id}/edit`}>
                    <Button variant="ghost" size="sm">
                      <Pencil className="h-3.5 w-3.5" /> Edit
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-400 hover:text-red-300"
                    onClick={() => setDeleteTarget(server)}
                    disabled={busy}
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Delete
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* Delete confirmation */}
      <Dialog open={deleteTarget !== null} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogHeader>
          <DialogTitle>Delete server?</DialogTitle>
          <DialogDescription>
            This permanently removes{" "}
            <span className="font-medium text-slate-200">{deleteTarget?.name}</span> (
            {deleteTarget?.ip_address}) and its encrypted credentials. This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
            {deleting && <Loader2 className="h-4 w-4 animate-spin" />} Delete
          </Button>
        </DialogFooter>
      </Dialog>
    </main>
  );
}

export default withAuth(ServersPage, ["admin", "super_admin"]);
