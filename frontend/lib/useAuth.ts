"use client";

import { useEffect, useState } from "react";
import Cookies from "js-cookie";

export type Role = "super_admin" | "admin" | "viewer";

export interface AuthUser {
  id: string;
  role: Role;
  email?: string;
  full_name?: string | null;
}

/** Decode a JWT payload client-side (read-only; the server still verifies it). */
export function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decodeURIComponent(escape(json)));
  } catch {
    return null;
  }
}

const ROLE_RANK: Record<Role, number> = { viewer: 1, admin: 2, super_admin: 3 };

/** Pages each role is allowed to access (route prefixes). */
export const ROUTE_ROLES: Record<string, Role[]> = {
  "/dashboard": ["viewer", "admin", "super_admin"],
  "/metrics": ["viewer", "admin", "super_admin"],
  "/ai-reports": ["viewer", "admin", "super_admin"],
  "/servers": ["admin", "super_admin"],
  "/security-alerts": ["admin", "super_admin"],
  "/audit-logs": ["super_admin"],
  "/settings": ["super_admin"],
};

export function rolesForPath(pathname: string): Role[] | null {
  const match = Object.keys(ROUTE_ROLES)
    .filter((prefix) => pathname === prefix || pathname.startsWith(prefix + "/"))
    .sort((a, b) => b.length - a.length)[0];
  return match ? ROUTE_ROLES[match] : null;
}

export function getRoleFromToken(): Role | null {
  const token = Cookies.get("access_token");
  if (!token) return null;
  const claims = decodeJwt(token);
  const role = claims?.role as Role | undefined;
  return role ?? null;
}

/**
 * Auth hook: exposes the current user (role from JWT, profile from /auth/me),
 * plus hasRole() and canAccess() helpers.
 */
export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = Cookies.get("access_token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    const claims = decodeJwt(token);
    const role = (claims?.role as Role) ?? "viewer";
    const id = (claims?.sub as string) ?? "";
    setUser({ id, role });

    // Enrich with profile info (name/email) from the API; non-blocking.
    import("@/lib/api").then(({ api }) => {
      api
        .get("/auth/me")
        .then(({ data }) => setUser({ id: data.id, role: data.role, email: data.email, full_name: data.full_name }))
        .catch(() => {})
        .finally(() => setLoading(false));
    });
  }, []);

  function hasRole(...roles: Role[]): boolean {
    return user ? roles.includes(user.role) : false;
  }

  function canAccess(pathname: string): boolean {
    if (!user) return false;
    const allowed = rolesForPath(pathname);
    return allowed ? allowed.includes(user.role) : true;
  }

  function atLeast(minimum: Role): boolean {
    return user ? ROLE_RANK[user.role] >= ROLE_RANK[minimum] : false;
  }

  return { user, loading, hasRole, canAccess, atLeast };
}
