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
