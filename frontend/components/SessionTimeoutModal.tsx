"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";
import { sessionManager } from "@/lib/sessionManager";
import { refreshSession } from "@/lib/api";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

/**
 * Warning modal shown 2 minutes before the inactivity timeout. Offers
 * "Stay Logged In" (refreshes the token + resets the timer) and "Logout Now".
 */
export function SessionTimeoutModal() {
  const [open, setOpen] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(120);

  useEffect(() => {
    const offWarn = sessionManager.on("warning", (s) => {
      setSecondsLeft(s);
      setOpen(true);
    });
    const offLogout = sessionManager.on("logout", () => setOpen(false));
    return () => {
      offWarn();
      offLogout();
    };
  }, []);

  // Live countdown while the modal is open.
  useEffect(() => {
    if (!open) return;
    const id = setInterval(() => setSecondsLeft(sessionManager.secondsLeft()), 1000);
    return () => clearInterval(id);
  }, [open]);

  async function stayLoggedIn() {
    const ok = await refreshSession();
    if (ok) {
      sessionManager.reset();
      setOpen(false);
    } else {
      sessionManager.logout();
    }
  }

  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && stayLoggedIn()}>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-amber-400" /> Session expiring soon
        </DialogTitle>
        <DialogDescription>
          You will be logged out in{" "}
          <span className="font-mono font-semibold text-amber-300">
            {mins}:{secs.toString().padStart(2, "0")}
          </span>{" "}
          due to inactivity. Stay logged in to continue.
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline" onClick={() => sessionManager.logout()}>
          Logout Now
        </Button>
        <Button onClick={stayLoggedIn}>Stay Logged In</Button>
      </DialogFooter>
    </Dialog>
  );
}
