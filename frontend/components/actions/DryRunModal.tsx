"use client";

import { type DryRunResult } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Terminal } from "lucide-react";

interface Props {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  result: DryRunResult | null;
  serverName: string;
  onProceed?: () => void;
}

export function DryRunModal({ open, onOpenChange, result, serverName, onProceed }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Terminal className="h-5 w-5 text-indigo-400" /> Dry Run Result
        </DialogTitle>
        <DialogDescription>
          {serverName} · {result?.server_ip}
        </DialogDescription>
      </DialogHeader>
      {result && (
        <div className="space-y-3">
          <div>
            <p className="mb-1 text-xs text-slate-500">Command</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-emerald-300">{result.exact_command_string}</pre>
          </div>
          <div>
            <p className="mb-1 text-xs text-slate-500">Output</p>
            <pre className="max-h-72 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-200">{result.output}</pre>
          </div>
          <p className="text-xs text-slate-500">Ran at {formatDateTime(result.executed_at)}</p>
        </div>
      )}
      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        {onProceed && <Button onClick={onProceed}>Proceed to Request Action</Button>}
      </DialogFooter>
    </Dialog>
  );
}
