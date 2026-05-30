import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** shadcn/ui-style class combiner: merges Tailwind classes intelligently. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Public app configuration sourced from NEXT_PUBLIC_* env vars (with defaults). */
export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8002",
  sessionTimeoutMinutes: Number(
    process.env.NEXT_PUBLIC_SESSION_TIMEOUT_MINUTES || "30",
  ),
};
