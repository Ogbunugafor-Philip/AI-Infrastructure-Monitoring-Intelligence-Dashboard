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
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-[#2d3748] bg-[#131625] px-6">
      <div className="text-sm font-semibold text-white">AI Infrastructure Monitor</div>
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2">
            <UserCircle2 className="h-6 w-6 text-[#94a3b8]" />
            <div className="hidden text-right sm:block">
              <div className="text-sm font-medium text-[#e2e8f0]">{displayName}</div>
            </div>
            <Badge variant={ROLE_VARIANT[user.role]}>{ROLE_LABEL[user.role]}</Badge>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 rounded-lg border border-[#2d3748] px-3 py-1.5 text-sm font-medium text-[#ef4444] transition hover:bg-[#2d1515]"
        >
          <LogOut className="h-4 w-4" /> Logout
        </button>
      </div>
    </header>
  );
}
