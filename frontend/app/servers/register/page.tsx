"use client";

import Link from "next/link";
import { ArrowLeft, ServerCog } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ServerForm } from "@/components/ServerForm";

export default function RegisterServerPage() {
  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-10">
      <Link
        href="/servers"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft className="h-4 w-4" /> Back to servers
      </Link>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ServerCog className="h-5 w-5 text-indigo-400" /> Register a Server
          </CardTitle>
          <CardDescription>
            Add a server to monitor. Credentials are encrypted (AES-256-GCM) before storage and
            never displayed. Test the connection before saving.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ServerForm mode="create" />
        </CardContent>
      </Card>
    </main>
  );
}
