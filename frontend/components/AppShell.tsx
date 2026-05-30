"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import Cookies from "js-cookie";
import { useAuth } from "@/lib/useAuth";
import { sessionManager } from "@/lib/sessionManager";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { SessionTimeoutModal } from "@/components/SessionTimeoutModal";

// Routes that render WITHOUT the dashboard chrome (no sidebar/header/session mgr).
const PUBLIC_ROUTES = ["/login", "/unauthorized"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const isPublic = PUBLIC_ROUTES.some((r) => pathname === r || pathname.startsWith(r + "/"));

  // Start the inactivity session manager + activity tracking on protected routes.
  useEffect(() => {
    if (isPublic) return;
    if (!Cookies.get("access_token")) return;

    sessionManager.start();
    const onActivity = () => sessionManager.reset();
    const events = ["mousemove", "keydown", "click", "scroll", "touchstart"];
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    return () => {
      events.forEach((e) => window.removeEventListener(e, onActivity));
      sessionManager.stop();
    };
  }, [isPublic]);

  if (isPublic) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {user && <Sidebar role={user.role} />}
      <div className="flex min-w-0 flex-1 flex-col">
        <Header user={user} />
        <main className="flex-1 overflow-y-auto bg-[#0f1117]">{children}</main>
      </div>
      <SessionTimeoutModal />
    </div>
  );
}
