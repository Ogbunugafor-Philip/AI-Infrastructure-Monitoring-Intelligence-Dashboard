"use client";

import { useCallback, useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { config, logoutAndRedirectPath } from "@/lib/session";

/**
 * Client component that logs the user out after a period of inactivity equal to
 * SESSION_INACTIVITY_TIMEOUT_MINUTES (from .env, surfaced via NEXT_PUBLIC_*).
 *
 * Any user activity (mouse, keyboard, scroll, touch) resets the idle timer.
 * On timeout, auth cookies are cleared and the user is redirected to /login.
 * The timer is inert on the public /login route.
 */
export default function SessionTimeout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timeoutMs = config.sessionTimeoutMinutes * 60 * 1000;

  const handleTimeout = useCallback(() => {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    router.replace(logoutAndRedirectPath());
  }, [router]);

  const resetTimer = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    // Do not arm the timer on the login page itself.
    if (pathname === "/login") return;
    timer.current = setTimeout(handleTimeout, timeoutMs);
  }, [handleTimeout, pathname, timeoutMs]);

  useEffect(() => {
    const events = ["mousemove", "mousedown", "keydown", "scroll", "touchstart", "click"];
    const onActivity = () => resetTimer();
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    resetTimer();
    return () => {
      events.forEach((e) => window.removeEventListener(e, onActivity));
      if (timer.current) clearTimeout(timer.current);
    };
  }, [resetTimer]);

  return <>{children}</>;
}
