import { type CommandCatalog, type CommandItem } from "@/lib/api";

/**
 * Best-effort mapping from a free-text AI recommendation (or scan fix hint) to
 * the closest whitelisted command_key. Returns the matching CommandItem or null
 * (null => manual execution required).
 */
const RULES: { keywords: string[]; key: string }[] = [
  { keywords: ["nginx", "restart"], key: "restart_nginx" },
  { keywords: ["nginx", "reload"], key: "reload_nginx" },
  { keywords: ["nginx", "status"], key: "check_nginx_status" },
  { keywords: ["postgres", "restart"], key: "restart_postgresql" },
  { keywords: ["postgres", "reload"], key: "reload_postgresql" },
  { keywords: ["postgres"], key: "check_postgresql_status" },
  { keywords: ["docker", "restart"], key: "restart_docker" },
  { keywords: ["docker"], key: "check_docker_containers" },
  { keywords: ["temp", "file"], key: "clear_temp_files" },
  { keywords: ["disk", "space"], key: "clear_temp_files" },
  { keywords: ["disk", "full"], key: "clear_temp_files" },
  { keywords: ["clear", "log"], key: "clear_old_logs" },
  { keywords: ["vacuum", "log"], key: "clear_old_logs" },
  { keywords: ["rotate", "log"], key: "rotate_logs" },
  { keywords: ["zombie", "kill"], key: "kill_zombie_processes" },
  { keywords: ["zombie"], key: "check_zombie_processes" },
  { keywords: ["firewall"], key: "check_firewall_status" },
  { keywords: ["ufw"], key: "check_firewall_status" },
  { keywords: ["dns", "cache"], key: "flush_dns_cache" },
  { keywords: ["failed", "systemd"], key: "clear_failed_systemd" },
  { keywords: ["reboot"], key: "reboot_server" },
  { keywords: ["memory"], key: "check_memory" },
  { keywords: ["open port"], key: "check_open_ports" },
  { keywords: ["large file"], key: "list_large_files" },
];

export function flattenCatalog(catalog: CommandCatalog): Record<string, CommandItem> {
  const map: Record<string, CommandItem> = {};
  [...catalog.low, ...catalog.medium, ...catalog.high].forEach((c) => {
    map[c.command_key] = c;
  });
  return map;
}

export function matchRecommendation(
  text: string,
  catalog: CommandCatalog,
): CommandItem | null {
  const lower = text.toLowerCase();
  const byKey = flattenCatalogSafe(catalog);
  let best: { key: string; score: number } | null = null;
  for (const rule of RULES) {
    const matched = rule.keywords.filter((k) => lower.includes(k)).length;
    if (matched === rule.keywords.length && byKey[rule.key]) {
      if (!best || matched > best.score) best = { key: rule.key, score: matched };
    }
  }
  return best ? byKey[best.key] : null;
}

function flattenCatalogSafe(catalog: CommandCatalog): Record<string, CommandItem> {
  const map: Record<string, CommandItem> = {};
  [...(catalog.low ?? []), ...(catalog.medium ?? []), ...(catalog.high ?? [])].forEach((c) => {
    map[c.command_key] = c;
  });
  return map;
}

export function findingBulletColor(text: string): string {
  const t = text.toLowerCase();
  if (/(error|critical|high|failed|unauthorized)/.test(t)) return "#ef4444";
  if (/(warning|elevated|unusual)/.test(t)) return "#f59e0b";
  return "#22c55e";
}
