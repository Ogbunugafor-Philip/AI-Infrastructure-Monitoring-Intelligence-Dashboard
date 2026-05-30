import { config as appConfig } from "@/lib/utils";

export const config = appConfig;

/** Path to send users to when their session expires (preserves intent simply). */
export function logoutAndRedirectPath(): string {
  return "/login?reason=session_expired";
}
