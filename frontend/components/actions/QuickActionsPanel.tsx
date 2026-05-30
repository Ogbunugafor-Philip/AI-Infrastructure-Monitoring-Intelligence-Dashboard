"use client";

import { useEffect, useState } from "react";
import { Zap } from "lucide-react";
import { type CommandItem, getCommands } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Button } from "@/components/ui/button";
import { ActionRequestModal } from "@/components/actions/ActionRequestModal";

// Curated common low-risk quick actions.
const QUICK_KEYS = [
  "check_disk_space",
  "check_memory",
  "check_cpu",
  "check_uptime",
  "list_running_services",
  "check_open_ports",
];

export function QuickActionsPanel({
  serverId,
  serverName,
  serverIp,
}: {
  serverId: string;
  serverName: string;
  serverIp: string;
}) {
  const { user } = useAuth();
  const [commands, setCommands] = useState<CommandItem[]>([]);
  const [active, setActive] = useState<CommandItem | null>(null);

  useEffect(() => {
    getCommands()
      .then((cat) => {
        const byKey = new Map(cat.low.map((c) => [c.command_key, c]));
        setCommands(QUICK_KEYS.map((k) => byKey.get(k)).filter(Boolean) as CommandItem[]);
      })
      .catch(() => setCommands([]));
  }, []);

  if (commands.length === 0) return null;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
        <Zap className="h-5 w-5 text-amber-400" /> Quick Actions
      </h2>
      <div className="flex flex-wrap gap-2">
        {commands.map((c) => (
          <Button key={c.command_key} variant="secondary" size="sm" onClick={() => setActive(c)}>
            {c.description}
          </Button>
        ))}
      </div>
      {active && (
        <ActionRequestModal
          open={!!active}
          onOpenChange={(o) => !o && setActive(null)}
          serverId={serverId}
          serverName={serverName}
          serverIp={serverIp}
          command={active}
          requesterEmail={user?.email ?? user?.id ?? "you"}
        />
      )}
    </section>
  );
}
