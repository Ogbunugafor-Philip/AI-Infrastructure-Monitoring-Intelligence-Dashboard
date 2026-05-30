"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Lock, ShieldAlert, Terminal } from "lucide-react";
import {
  type ActionRecord,
  type CommandItem,
  errorMessage,
  executeAction,
  getActionStatus,
  requestAction,
  verifyActionPassword,
} from "@/lib/api";
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
import { Badge } from "@/components/ui/badge";

type Step = "loading" | "review" | "password" | "approved" | "awaiting" | "done" | "expired" | "error";

const RISK_BADGE: Record<string, "online" | "warning" | "default"> = {
  low: "online",
  medium: "warning",
  high: "default",
};

interface Props {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  serverId: string;
  serverName: string;
  serverIp: string;
  command: CommandItem;
  requesterEmail: string;
  onDone?: () => void;
}

export function ActionRequestModal({
  open,
  onOpenChange,
  serverId,
  serverName,
  serverIp,
  command,
  requesterEmail,
  onDone,
}: Props) {
  const [step, setStep] = useState<Step>("loading");
  const [action, setAction] = useState<ActionRecord | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [output, setOutput] = useState<string | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(60);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isHigh = command.risk_level === "high";

  // Create the pending action when the modal opens.
  useEffect(() => {
    if (!open) return;
    setStep("loading");
    setError(null);
    setPassword("");
    setOutput(null);
    requestAction(serverId, command.command_key)
      .then((a) => {
        setAction(a);
        setStep("review");
      })
      .catch((e) => {
        setError(errorMessage(e, "Could not create the action request."));
        setStep("error");
      });
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [open, serverId, command.command_key]);

  const startAwaiting = useCallback((a: ActionRecord) => {
    setStep("awaiting");
    const deadline = a.time_lock_expires_at ? new Date(a.time_lock_expires_at).getTime() : Date.now() + 60000;
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setSecondsLeft(left);
      try {
        const fresh = await getActionStatus(a.id);
        setAction(fresh);
        if (fresh.second_confirmation_received && fresh.status === "approved") {
          if (pollRef.current) clearInterval(pollRef.current);
          setStep("approved");
        } else if (fresh.status === "expired" || left <= 0) {
          if (pollRef.current) clearInterval(pollRef.current);
          setStep("expired");
        }
      } catch {
        /* keep polling */
      }
    }, 2000);
  }, []);

  async function handleVerify() {
    if (!action) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await verifyActionPassword(action.id, password);
      setAction(updated);
      if (isHigh) {
        setSecondsLeft(60);
        startAwaiting(updated);
      } else {
        setStep("approved");
      }
    } catch (e) {
      setError(errorMessage(e, "Password verification failed."));
    } finally {
      setBusy(false);
    }
  }

  async function handleExecute() {
    if (!action) return;
    setBusy(true);
    setError(null);
    try {
      const done = await executeAction(action.id);
      setOutput(done.execution_output ?? "(no output)");
      setStep("done");
      onDone?.();
    } catch (e) {
      setError(errorMessage(e, "Execution failed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Terminal className="h-5 w-5 text-indigo-400" /> Run Action
        </DialogTitle>
        <DialogDescription>
          {command.description} · <Badge variant={RISK_BADGE[command.risk_level]}>{command.risk_level}</Badge>
        </DialogDescription>
      </DialogHeader>

      {step === "loading" && (
        <div className="flex items-center gap-2 py-6 text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" /> Preparing action…
        </div>
      )}

      {step === "error" && <Alert variant="destructive">{error}</Alert>}

      {step === "review" && (
        <div className="space-y-4">
          <div>
            <p className="text-xs text-slate-500">Target server</p>
            <p className="text-lg font-semibold">{serverName}</p>
            <p className="font-mono text-sm text-slate-400">{serverIp}</p>
          </div>
          <div>
            <p className="mb-1 text-xs text-slate-500">Exact command</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-emerald-300">{command.command_string}</pre>
          </div>
          <p className="text-xs text-slate-500">Requested by {requesterEmail}</p>
          {isHigh && (
            <Alert variant="destructive">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <span>High risk: requires a second Admin/Super Admin confirmation within a 60-second time lock after you verify your password.</span>
            </Alert>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button onClick={() => setStep("password")}>Continue</Button>
          </DialogFooter>
        </div>
      )}

      {step === "password" && (
        <div className="space-y-3">
          <Alert variant="warning">
            <Lock className="mt-0.5 h-4 w-4 shrink-0" />
            <span>You are about to run <span className="font-mono">{command.command_key}</span> on {serverName}.</span>
          </Alert>
          {error && <Alert variant="destructive">{error}</Alert>}
          <div>
            <Label htmlFor="action-pw">Enter your dashboard password to continue</Label>
            <Input id="action-pw" type="password" autoFocus value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStep("review")}>Back</Button>
            <Button onClick={handleVerify} disabled={busy || !password}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />} Verify Password
            </Button>
          </DialogFooter>
        </div>
      )}

      {step === "awaiting" && (
        <div className="space-y-4 text-center">
          <ShieldAlert className="mx-auto h-10 w-10 text-amber-400" />
          <p className="font-semibold">Awaiting Second Confirmation</p>
          <div className="text-4xl font-bold tabular-nums text-amber-300">{secondsLeft}s</div>
          <p className="text-sm text-slate-400">A second Admin or Super Admin must confirm this action within 60 seconds.</p>
        </div>
      )}

      {step === "expired" && (
        <div className="space-y-4 text-center">
          <AlertTriangle className="mx-auto h-10 w-10 text-red-400" />
          <p className="font-semibold">Action Expired</p>
          <p className="text-sm text-slate-400">The 60-second confirmation window passed without a second approval.</p>
          <DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button></DialogFooter>
        </div>
      )}

      {step === "approved" && (
        <div className="space-y-4 text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-400" />
          <p className="font-semibold">Action Approved</p>
          {action?.confirmed_by_user_id && (
            <p className="text-xs text-slate-500">Second confirmation received.</p>
          )}
          {error && <Alert variant="destructive">{error}</Alert>}
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button onClick={handleExecute} disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />} Execute Now
            </Button>
          </DialogFooter>
        </div>
      )}

      {step === "done" && (
        <div className="space-y-3">
          <Alert variant="success">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> Action completed.
          </Alert>
          <div>
            <p className="mb-1 text-xs text-slate-500">Output</p>
            <pre className="max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-200">{output}</pre>
          </div>
          <DialogFooter><Button onClick={() => onOpenChange(false)}>Close</Button></DialogFooter>
        </div>
      )}
    </Dialog>
  );
}
