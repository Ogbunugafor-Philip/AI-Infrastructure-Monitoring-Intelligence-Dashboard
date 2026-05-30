"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BrainCircuit,
  LayoutDashboard,
  ScrollText,
  ServerCog,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Terminal,
} from "lucide-react";
import { type Role } from "@/lib/useAuth";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: Role[];
}

const ALL: Role[] = ["viewer", "admin", "super_admin"];

// Items are REMOVED from the DOM for roles not listed.
const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ALL },
  { href: "/servers", label: "Servers", icon: ServerCog, roles: ["admin", "super_admin"] },
  { href: "/metrics", label: "Metrics", icon: Activity, roles: ALL },
  { href: "/actions", label: "Actions", icon: Terminal, roles: ["admin", "super_admin"] },
  { href: "/ai-reports", label: "AI Reports", icon: BrainCircuit, roles: ALL },
  { href: "/audit-logs", label: "Audit Logs", icon: ScrollText, roles: ["super_admin"] },
  { href: "/security-alerts", label: "Security Alerts", icon: ShieldAlert, roles: ["admin", "super_admin"] },
  { href: "/settings", label: "Settings", icon: Settings, roles: ALL },
];

export function Sidebar({ role }: { role: Role }) {
  const pathname = usePathname();
  const items = NAV.filter((item) => item.roles.includes(role));

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-[#2d3748] bg-[#131625] md:flex">
      <div className="flex h-16 items-center gap-2 border-b border-[#2d3748] px-5">
        <ShieldCheck className="h-6 w-6 text-[#3b82f6]" />
        <span className="text-sm font-semibold leading-tight text-white">
          AI Infra<br />
          <span className="text-[#94a3b8]">Monitor</span>
        </span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-[#3b82f6]/10 text-[#3b82f6] underline decoration-2 underline-offset-4"
                  : "text-[#94a3b8] hover:bg-[#1e2235] hover:text-white",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-[#2d3748] p-4 text-xs text-[#64748b]">
        Secured • RBAC • Audited
      </div>
    </aside>
  );
}
