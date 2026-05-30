import axios from "axios";
import Cookies from "js-cookie";
import { config } from "@/lib/utils";

/**
 * Shared axios client for the backend API.
 *
 * The access token is read from a cookie and attached as a Bearer header.
 * Tokens are NOT logged anywhere. `withCredentials` is enabled so the backend
 * can also rely on cookies if desired.
 */
export const api = axios.create({
  baseURL: `${config.apiUrl}/api/v1`,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((cfg) => {
  const token = Cookies.get("access_token");
  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`;
  }
  return cfg;
});

// Global response handling:
//  - 401: clear tokens and redirect to /login
//  - 403: redirect to /unauthorized
// The /auth/verify-password call opts out (403 there is an expected outcome).
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (typeof window !== "undefined" && error?.response) {
      const status = error.response.status;
      const url: string = error.config?.url ?? "";
      const optOut = url.includes("/auth/verify-password");
      if (status === 401) {
        Cookies.remove("access_token");
        Cookies.remove("refresh_token");
        if (!window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
      } else if (status === 403 && !optOut) {
        if (!window.location.pathname.startsWith("/unauthorized")) {
          window.location.href = "/unauthorized";
        }
      }
    }
    return Promise.reject(error);
  },
);

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", { email, password });
  return data;
}

export async function logout(): Promise<void> {
  const refresh = Cookies.get("refresh_token");
  try {
    if (refresh) {
      await api.post("/auth/logout", { refresh_token: refresh });
    }
  } finally {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
  }
}

// --------------------------------------------------------------------------- //
// Server management types & API                                               //
// --------------------------------------------------------------------------- //
export type AuthMethod = "password" | "key";
export type ServerStatus = "online" | "offline" | "warning";

export interface Server {
  id: string;
  name: string;
  ip_address: string;
  ssh_port: number;
  ssh_username: string;
  ssh_auth_method: AuthMethod;
  ssh_key_only_mode: boolean;
  allowed_ip_whitelist: string | null;
  status: ServerStatus;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  ssh_password: string | null; // masked ("••••••••") or null
  ssh_key: string | null; // masked ("••••••••") or null
}

export interface ServerCreatePayload {
  name: string;
  ip_address: string;
  ssh_port: number;
  ssh_username: string;
  ssh_auth_method: AuthMethod;
  ssh_password?: string | null;
  ssh_key?: string | null;
  ssh_key_only_mode: boolean;
  allowed_ip_whitelist?: string | null;
}

export interface TestConnectionPayload {
  server_id?: string;
  ip_address?: string;
  ssh_port?: number;
  ssh_username?: string;
  ssh_auth_method?: AuthMethod;
  ssh_password?: string | null;
  ssh_key?: string | null;
  ssh_key_only_mode?: boolean;
}

export interface TestConnectionResult {
  success: boolean;
  message: string;
}

export async function listServers(): Promise<Server[]> {
  const { data } = await api.get<Server[]>("/servers/");
  return data;
}

export async function getServer(id: string): Promise<Server> {
  const { data } = await api.get<Server>(`/servers/${id}`);
  return data;
}

export async function registerServer(payload: ServerCreatePayload): Promise<Server> {
  const { data } = await api.post<Server>("/servers/register", payload);
  return data;
}

export async function updateServer(
  id: string,
  payload: Partial<ServerCreatePayload> & { status?: ServerStatus },
): Promise<Server> {
  const { data } = await api.put<Server>(`/servers/${id}`, payload);
  return data;
}

export async function deleteServer(id: string): Promise<void> {
  await api.delete(`/servers/${id}`);
}

export async function testConnection(
  payload: TestConnectionPayload,
): Promise<TestConnectionResult> {
  const { data } = await api.post<TestConnectionResult>("/servers/test-connection", payload);
  return data;
}

export async function toggleKeyOnly(id: string): Promise<Server> {
  const { data } = await api.post<Server>(`/servers/${id}/toggle-key-only`, {});
  return data;
}

export interface RevealResult {
  auth_method: AuthMethod;
  credential: string;
}

export async function revealCredentials(
  id: string,
  dashboardPassword: string,
): Promise<RevealResult> {
  const { data } = await api.post<RevealResult>(`/servers/${id}/reveal-credentials`, {
    dashboard_password: dashboardPassword,
  });
  return data;
}

// --------------------------------------------------------------------------- //
// Dashboard & metrics types                                                   //
// --------------------------------------------------------------------------- //
export interface Overview {
  total_servers: number;
  servers_online: number;
  servers_offline: number;
  servers_warning: number;
  avg_cpu_usage: number;
  avg_ram_usage: number;
  avg_disk_usage: number;
  security_alerts_24h: number;
  audit_events_24h: number;
}

export interface ServerStatusItem {
  id: string;
  name: string;
  ip_address: string;
  ssh_port: number;
  ssh_username: string;
  ssh_auth_method: AuthMethod;
  ssh_key_only_mode: boolean;
  status: ServerStatus;
  cpu_usage: number | null;
  ram_usage: number | null;
  disk_usage: number | null;
  uptime: string | null;
  last_updated: string | null;
}

export type Severity = "high" | "medium" | "low";

export interface SecurityAlert {
  id: string;
  event_type: string;
  event_description: string | null;
  ip_address: string | null;
  user_id: string | null;
  target_server_id: string | null;
  success: boolean;
  severity: Severity;
  created_at: string;
}

export interface AuditLogItem {
  id: string;
  user_id: string | null;
  event_type: string;
  event_description: string | null;
  ip_address: string | null;
  target_server_id: string | null;
  success: boolean;
  created_at: string;
}

export interface AuditLogPage {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProcessInfo {
  name: string;
  pid: number | string;
  cpu: number | null;
  memory: number | null;
  status: string;
}

export interface PortInfo {
  port: number | string;
  protocol: string;
  service: string;
  state: string;
  process: string;
}

export interface Metric {
  id: string;
  server_id: string;
  cpu_usage: number | null;
  ram_usage: number | null;
  disk_usage: number | null;
  uptime: string | null;
  running_processes: ProcessInfo[] | null;
  open_ports: PortInfo[] | null;
  network_stats: Record<string, number> | null;
  collected_at: string;
}

export interface MetricHistoryPoint {
  collected_at: string;
  cpu_usage: number | null;
  ram_usage: number | null;
  disk_usage: number | null;
}

export interface MetricHistory {
  server_id: string;
  hours: number;
  points: MetricHistoryPoint[];
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: "super_admin" | "admin" | "viewer";
  is_active: boolean;
}

export async function getMe(): Promise<UserProfile> {
  const { data } = await api.get<UserProfile>("/auth/me");
  return data;
}

export async function getOverview(): Promise<Overview> {
  const { data } = await api.get<Overview>("/dashboard/overview");
  return data;
}

export async function getServersStatus(): Promise<ServerStatusItem[]> {
  const { data } = await api.get<ServerStatusItem[]>("/dashboard/servers/status");
  return data;
}

export async function getSecurityAlerts(limit = 50): Promise<SecurityAlert[]> {
  const { data } = await api.get<SecurityAlert[]>(`/dashboard/security-alerts?limit=${limit}`);
  return data;
}

export interface AuditLogQuery {
  page?: number;
  page_size?: number;
  event_type?: string;
  date_from?: string;
  date_to?: string;
  user_id?: string;
  server_id?: string;
}

export async function getAuditLogs(query: AuditLogQuery): Promise<AuditLogPage> {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const { data } = await api.get<AuditLogPage>(`/dashboard/audit-logs?${params.toString()}`);
  return data;
}

/** Download the audit-log CSV export through the authenticated axios client. */
export async function downloadAuditCsv(query: AuditLogQuery = {}): Promise<void> {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const response = await api.get(`/dashboard/audit-logs/export?${params.toString()}`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function getLatestMetric(serverId: string): Promise<Metric | null> {
  const { data } = await api.get<Metric | null>(`/metrics/${serverId}/latest`);
  return data;
}

export async function getMetricHistory(serverId: string, hours = 24): Promise<MetricHistory> {
  const { data } = await api.get<MetricHistory>(`/metrics/${serverId}/history?hours=${hours}`);
  return data;
}

export async function refreshMetrics(
  serverId: string,
): Promise<{ success: boolean; message: string; metric: Metric | null }> {
  const { data } = await api.post(`/metrics/${serverId}/refresh`, {});
  return data;
}

/** Refresh the session by rotating the refresh token ("Stay Logged In"). */
export async function refreshSession(): Promise<boolean> {
  const refresh = Cookies.get("refresh_token");
  if (!refresh) return false;
  try {
    const { data } = await api.post<TokenResponse>("/auth/refresh", { refresh_token: refresh });
    Cookies.set("access_token", data.access_token, {
      secure: true,
      sameSite: "strict",
      expires: data.expires_in / 86400,
    });
    Cookies.set("refresh_token", data.refresh_token, { secure: true, sameSite: "strict" });
    return true;
  } catch {
    return false;
  }
}

/** Verify the current user's dashboard password (used as a reveal gate). */
export async function verifyPassword(password: string): Promise<boolean> {
  try {
    await api.post("/auth/verify-password", { password });
    return true;
  } catch {
    return false;
  }
}

/** Extract a human-friendly message from an axios error (no internals leaked). */
export function errorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (typeof err === "object" && err !== null && "response" in err) {
    const resp = (err as { response?: { status?: number; data?: { detail?: unknown } } }).response;
    if (resp?.status === 429) return "Too many requests. Please wait and try again.";
    const detail = resp?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === "string") {
      return detail[0].msg;
    }
  }
  return fallback;
}
