"use client";

import { Settings as SettingsIcon } from "lucide-react";
import { withAuth } from "@/lib/withAuth";
import { useAuth } from "@/lib/useAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function SettingsPage() {
  const { user } = useAuth();
  return (
    <div className="space-y-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-semibold">
        <SettingsIcon className="h-6 w-6 text-indigo-400" /> Settings
      </h1>
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Super-admin configuration area.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-slate-300">
          <div className="flex justify-between border-b border-slate-800 py-2">
            <span className="text-slate-500">Signed in as</span>
            <span className="font-mono">{user?.email ?? user?.id ?? "—"}</span>
          </div>
          <div className="flex justify-between border-b border-slate-800 py-2">
            <span className="text-slate-500">Role</span>
            <span>{user?.role ?? "—"}</span>
          </div>
          <p className="pt-2 text-xs text-slate-500">
            Additional system settings (retention, SMTP, scheduler) are managed via the server
            .env configuration.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default withAuth(SettingsPage, ["super_admin"]);
