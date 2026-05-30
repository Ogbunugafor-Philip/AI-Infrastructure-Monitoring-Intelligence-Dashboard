import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressProps {
  value: number; // 0-100
  className?: string;
  showLabel?: boolean;
}

/** Threshold colour: green < 60, yellow 60-80, red > 80. */
export function usageColor(value: number): string {
  if (value > 80) return "bg-red-500";
  if (value >= 60) return "bg-amber-500";
  return "bg-emerald-500";
}

export function Progress({ value, className, showLabel }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="flex items-center gap-2">
      <div className={cn("h-2 w-full overflow-hidden rounded-full bg-slate-800", className)}>
        <div
          className={cn("h-full rounded-full transition-all", usageColor(clamped))}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showLabel && (
        <span className="w-10 shrink-0 text-right text-xs tabular-nums text-slate-400">
          {clamped.toFixed(0)}%
        </span>
      )}
    </div>
  );
}
