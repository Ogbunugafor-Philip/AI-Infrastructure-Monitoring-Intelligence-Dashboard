"use client";

import Cookies from "js-cookie";
import { config } from "@/lib/utils";

/**
 * Inactivity session manager (singleton).
 *
 * Tracks the last activity timestamp in memory, resets on user interaction, and
 * fires:
 *   - a "warning" event 2 minutes before the inactivity timeout expires, and
 *   - a "logout" event at expiry.
 * On logout it clears tokens and redirects to /login.
 */
type SessionEvent = "warning" | "logout";
type Listener = (secondsLeft: number) => void;

const WARNING_LEAD_MS = 2 * 60 * 1000; // 2 minutes before expiry

class SessionManager {
  private timeoutMs = config.sessionTimeoutMinutes * 60 * 1000;
  private lastActivity = Date.now();
  private interval: ReturnType<typeof setInterval> | null = null;
  private listeners: Record<SessionEvent, Set<Listener>> = {
    warning: new Set(),
    logout: new Set(),
  };
  private warned = false;
  private started = false;

  on(event: SessionEvent, fn: Listener): () => void {
    this.listeners[event].add(fn);
    return () => this.listeners[event].delete(fn);
  }

  private emit(event: SessionEvent, secondsLeft: number) {
    this.listeners[event].forEach((fn) => fn(secondsLeft));
  }

  /** Reset the inactivity timer (called on any user interaction). */
  reset() {
    this.lastActivity = Date.now();
    this.warned = false;
  }

  start() {
    if (this.started) return;
    this.started = true;
    this.reset();
    this.interval = setInterval(() => this.tick(), 1000);
  }

  stop() {
    if (this.interval) clearInterval(this.interval);
    this.interval = null;
    this.started = false;
  }

  private tick() {
    const elapsed = Date.now() - this.lastActivity;
    const remaining = this.timeoutMs - elapsed;

    if (remaining <= 0) {
      this.logout();
      return;
    }
    if (remaining <= WARNING_LEAD_MS && !this.warned) {
      this.warned = true;
      this.emit("warning", Math.ceil(remaining / 1000));
    }
  }

  /** Seconds remaining before expiry (for the countdown in the warning modal). */
  secondsLeft(): number {
    return Math.max(0, Math.ceil((this.timeoutMs - (Date.now() - this.lastActivity)) / 1000));
  }

  logout() {
    this.stop();
    this.emit("logout", 0);
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    if (typeof window !== "undefined") {
      window.location.href = "/login?reason=session_expired";
    }
  }
}

export const sessionManager = new SessionManager();
