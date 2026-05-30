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
} from "lucide-react";
import { type Role } from "@/lib/useAuth";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: Role[];
}

// Navigation definition. Items are REMOVED from the DOM for roles not listed.
const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["viewer", "admin", "super_admin"] },
  { href: "/servers", label: "Servers", icon: ServerCog, roles: ["admin", "super_admin"] },
  { href: "/metrics", label: "Metrics", icon: Activity, roles: ["viewer", "admin", "super_admin"] },
  { href: "/ai-reports", label: "AI Reports", icon: BrainCircuit, roles: ["viewer", "admin", "super_admin"] },
  { href: "/audit-logs", label: "Audit Logs", icon: ScrollText, roles: ["super_admin"] },
  { href: "/security-alerts", label: "Security Alerts", icon: ShieldAlert, roles: ["admin", "super_admin"] },
  { href: "/settings", label: "Settings", icon: Settings, roles: ["super_admin"] },
];

export function Sidebar({ role }: { role: Role }) {
  const pathname = usePathname();
  const items = NAV.filter((item) => item.roles.includes(role));

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950 md:flex">
      <div className="flex h-16 items-center gap-2 border-b border-slate-800 px-5">
        <ShieldCheck className="h-6 w-6 text-indigo-400" />
        <span className="text-sm font-semibold leading-tight">
          AI Infra<br />
          <span className="text-slate-400">Monitoring</span>
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
                  ? "bg-indigo-600/20 text-indigo-300"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-slate-800 p-4 text-xs text-slate-600">
        Secured • RBAC • Audited
      </div>
    </aside>
  );
}
