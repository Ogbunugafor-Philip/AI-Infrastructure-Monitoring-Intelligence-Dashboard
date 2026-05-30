"use client";

import { useRouter } from "next/navigation";
import { LogOut, UserCircle2 } from "lucide-react";
import { type AuthUser, type Role } from "@/lib/useAuth";
import { logout } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const ROLE_LABEL: Record<Role, string> = {
  super_admin: "Super Admin",
  admin: "Admin",
  viewer: "Viewer",
};

// Role badge colour mapping.
const ROLE_VARIANT: Record<Role, "accent" | "online" | "warning"> = {
  super_admin: "accent",
  admin: "online",
  viewer: "warning",
};

export function Header({ user }: { user: AuthUser | null }) {
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  const displayName = user?.full_name || user?.email || "User";

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 backdrop-blur">
      <div className="text-sm text-slate-500">AI Infrastructure Monitoring &amp; Intelligence</div>
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2">
            <UserCircle2 className="h-6 w-6 text-slate-400" />
            <div className="hidden text-right sm:block">
              <div className="text-sm font-medium text-slate-200">{displayName}</div>
            </div>
            <Badge variant={ROLE_VARIANT[user.role]}>{ROLE_LABEL[user.role]}</Badge>
          </div>
        )}
        <Button variant="outline" size="sm" onClick={handleLogout}>
          <LogOut className="h-4 w-4" /> Logout
        </Button>
      </div>
    </header>
  );
}
