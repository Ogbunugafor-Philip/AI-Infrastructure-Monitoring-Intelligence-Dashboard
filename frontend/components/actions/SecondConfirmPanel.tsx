"use client";

import { useCallback, useEffect, useState } from "react";
import { ShieldAlert, Loader2 } from "lucide-react";
import {
  type ActionRecord,
  cancelAction,
  getAwaitingConfirmation,
  secondConfirmAction,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function Countdown({ deadline }: { deadline: string | null }) {
  const [left, setLeft] = useState(0);
  useEffect(() => {
    const end = deadline ? new Date(deadline).getTime() : Date.now();
    const tick = () => setLeft(Math.max(0, Math.ceil((end - Date.now()) / 1000)));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [deadline]);
  return <span className={`font-mono tabular-nums ${left <= 10 ? "text-red-400" : "text-amber-300"}`}>{left}s</span>;
}

/** Panel listing high-risk actions awaiting THIS user's second confirmation. */
export function SecondConfirmPanel({ onChange }: { onChange?: () => void }) {
  const [actions, setActions] = useState<ActionRecord[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setActions(await getAwaitingConfirmation());
    } catch {
      setActions([]);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000); // auto-refresh every 5s
    return () => clearInterval(id);
  }, [load]);

  async function confirm(id: string) {
    setBusyId(id);
    try {
      await secondConfirmAction(id);
      await load();
      onChange?.();
    } catch {
      await load();
    } finally {
      setBusyId(null);
    }
  }

  async function cancel(id: string) {
    setBusyId(id);
    try {
      await cancelAction(id);
      await load();
      onChange?.();
    } finally {
      setBusyId(null);
    }
  }

  if (actions.length === 0) return null;

  return (
    <div className="rounded-2xl border border-red-900/50 bg-red-950/20 p-5">
      <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-red-200">
        <ShieldAlert className="h-5 w-5" /> Pending High Risk Actions Awaiting Your Confirmation
      </h2>
      <div className="space-y-3">
        {actions.map((a) => (
          <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Badge variant="default">{a.command_key}</Badge>
                <span className="text-sm text-slate-300">{a.server_name}</span>
                <span className="font-mono text-xs text-slate-500">{a.server_ip}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Requested by another admin · time remaining <Countdown deadline={a.time_lock_expires_at} />
              </p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => confirm(a.id)} disabled={busyId === a.id}>
                {busyId === a.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null} Confirm
              </Button>
              <Button size="sm" variant="outline" onClick={() => cancel(a.id)} disabled={busyId === a.id}>
                Cancel
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
