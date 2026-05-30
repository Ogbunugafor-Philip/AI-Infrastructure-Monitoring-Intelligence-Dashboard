"use client";

import { useState } from "react";
import { Loader2, Skull } from "lucide-react";
import { emergencyKill, errorMessage } from "@/lib/api";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";

/** Super-admin only Danger Zone control: revoke creds + cancel all actions. */
export function EmergencyKillButton({
  serverId,
  serverName,
  serverIp,
  onKilled,
}: {
  serverId: string;
  serverName: string;
  serverIp: string;
  onKilled?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await emergencyKill(serverId, password);
      setDone(true);
      onKilled?.();
    } catch (e) {
      setError(errorMessage(e, "Emergency kill failed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-red-900/60 bg-red-950/20 p-5">
      <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-red-300">
        <Skull className="h-5 w-5" /> Danger Zone
      </h2>
      <p className="mb-3 text-sm text-slate-400">
        Immediately revoke all SSH credentials for this server and cancel all pending actions.
      </p>
      <Button variant="destructive" onClick={() => { setOpen(true); setDone(false); setPassword(""); setError(null); }}>
        <Skull className="h-4 w-4" /> Emergency Kill Switch
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogHeader>
          <DialogTitle className="text-red-400">EMERGENCY KILL SWITCH</DialogTitle>
          <DialogDescription>
            <span className="block text-base font-semibold text-slate-200">{serverName}</span>
            <span className="font-mono text-sm text-slate-400">{serverIp}</span>
          </DialogDescription>
        </DialogHeader>
        {done ? (
          <Alert variant="success">
            Credentials revoked and all pending actions cancelled. The server is now offline.
          </Alert>
        ) : (
          <div className="space-y-3">
            <Alert variant="destructive">
              This will immediately revoke all SSH credentials for this server and cancel all pending
              actions. This cannot be undone.
            </Alert>
            {error && <Alert variant="destructive">{error}</Alert>}
            <div>
              <Label htmlFor="kill-pw">Enter your dashboard password</Label>
              <Input id="kill-pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </div>
          </div>
        )}
        <DialogFooter>
          {done ? (
            <Button onClick={() => setOpen(false)}>Close</Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button variant="destructive" onClick={confirm} disabled={busy || !password}>
                {busy && <Loader2 className="h-4 w-4 animate-spin" />} Confirm Emergency Kill
              </Button>
            </>
          )}
        </DialogFooter>
      </Dialog>
    </div>
  );
}
