"use client";

import Link from "next/link";
import { ShieldX } from "lucide-react";
import { useAuth } from "@/lib/useAuth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super Admin",
  admin: "Admin",
  viewer: "Viewer",
};

export default function UnauthorizedPage() {
  const { user } = useAuth();
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/60 p-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-red-600/20 text-red-400">
          <ShieldX className="h-7 w-7" />
        </div>
        <h1 className="text-xl font-semibold">Access denied</h1>
        <p className="mt-2 text-sm text-slate-400">
          You don&apos;t have permission to view this page.
        </p>
        {user && (
          <p className="mt-4 text-sm text-slate-400">
            Your current role:{" "}
            <Badge variant="accent">{ROLE_LABEL[user.role] ?? user.role}</Badge>
          </p>
        )}
        <Link href="/dashboard" className="mt-6 inline-block">
          <Button>Back to Dashboard</Button>
        </Link>
      </div>
    </main>
  );
}
