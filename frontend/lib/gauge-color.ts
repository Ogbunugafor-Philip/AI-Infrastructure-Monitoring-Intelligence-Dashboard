/** Threshold colour (hex) for usage gauges: green < 60, yellow 60-80, red > 80. */
export function usageColorHex(value: number): string {
  if (value > 80) return "#ef4444";
  if (value >= 60) return "#f59e0b";
  return "#10b981";
}

/** Risk-score colour for AI reports: green 1-3, yellow 4-6, red 7-10. */
export function riskColor(score: number): string {
  if (score >= 7) return "#ef4444";
  if (score >= 4) return "#f59e0b";
  return "#10b981";
}
