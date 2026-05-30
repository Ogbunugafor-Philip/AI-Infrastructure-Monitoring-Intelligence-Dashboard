"use client";

import { useState } from "react";
import { Loader2, ShieldAlert } from "lucide-react";
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

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  /** Resolve true to accept, or return an error string to display. */
  onConfirm: (password: string) => Promise<true | string>;
  onSuccess?: () => void;
}

/**
 * Reusable modal that re-prompts for the dashboard password before a sensitive
 * action (revealing an SSH key/credential). The password is never stored.
 */
export function PasswordPromptDialog({
  open,
  onOpenChange,
  title = "Confirm your password",
  description = "Re-enter your dashboard password to reveal this sensitive value.",
  onConfirm,
  onSuccess,
}: Props) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await onConfirm(password);
      if (result === true) {
        setPassword("");
        onOpenChange(false);
        onSuccess?.();
      } else {
        setError(result);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { setPassword(""); setError(null); } onOpenChange(o); }}>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-amber-400" /> {title}
        </DialogTitle>
        <DialogDescription>{description}</DialogDescription>
      </DialogHeader>
      <form onSubmit={submit} className="space-y-3">
        {error && <Alert variant="destructive">{error}</Alert>}
        <div>
          <Label htmlFor="confirm-password">Dashboard password</Label>
          <Input
            id="confirm-password"
            type="password"
            autoFocus
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading || !password}>
            {loading && <Loader2 className="h-4 w-4 animate-spin" />} Confirm
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}
