"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, ServerCog } from "lucide-react";
import { type Server, errorMessage, getServer } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { ServerForm } from "@/components/ServerForm";

export default function EditServerPage({
  params,
}: {
  params: Promise<{ server_id: string }>;
}) {
  const { server_id } = use(params);
  const [server, setServer] = useState<Server | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getServer(server_id)
      .then(setServer)
      .catch((err) => setError(errorMessage(err, "Could not load server.")))
      .finally(() => setLoading(false));
  }, [server_id]);

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
            <ServerCog className="h-5 w-5 text-indigo-400" /> Edit Server
          </CardTitle>
          <CardDescription>
            Update server details. Leave credential fields blank to keep the stored values.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="flex items-center gap-2 text-slate-400">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          )}
          {error && <Alert variant="destructive">{error}</Alert>}
          {server && <ServerForm mode="edit" server={server} />}
        </CardContent>
      </Card>
    </main>
  );
}
