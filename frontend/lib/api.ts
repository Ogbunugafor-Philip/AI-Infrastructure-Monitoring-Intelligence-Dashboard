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
