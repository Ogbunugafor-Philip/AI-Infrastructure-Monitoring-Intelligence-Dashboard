"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { type Role, getRoleFromToken, rolesForPath } from "@/lib/useAuth";
import { PageSkeleton } from "@/components/Skeletons";

/**
 * Higher-order component enforcing RBAC at the page level.
 *
 * - No token            -> redirect to /login
 * - Role not permitted  -> redirect to /unauthorized
 * Enforcement does NOT rely on hidden UI; the page never renders for an
 * unauthorized role.
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  allowedRoles?: Role[],
) {
  return function Guarded(props: P) {
    const router = useRouter();
    const pathname = usePathname();
    const [state, setState] = useState<"checking" | "ok">("checking");

    useEffect(() => {
      const token = Cookies.get("access_token");
      if (!token) {
        router.replace("/login");
        return;
      }
      const role = getRoleFromToken();
      const required = allowedRoles ?? rolesForPath(pathname) ?? null;
      if (role && required && !required.includes(role)) {
        router.replace("/unauthorized");
        return;
      }
      setState("ok");
    }, [router, pathname]);

    if (state === "checking") return <PageSkeleton />;
    return <Component {...props} />;
  };
}
