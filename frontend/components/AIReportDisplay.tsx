"use client";

import { BrainCircuit, Loader2, PlayCircle, ShieldAlert, Zap } from "lucide-react";
import { type AiReport } from "@/lib/api";
import { riskColor } from "@/lib/gauge-color";
import { formatDateTime } from "@/lib/format";
import { Button } from "@/components/ui/button";

interface Normalized {
  summary: string;
  riskScore: number | null;
  riskLevel: string | null;
  keyFindings: string[];
  recommendedActions: string[];
  securityObservations: string[];
  performanceObservations: string[];
  ok: boolean; // false => could not parse a JSON-looking summary
}

/** Loosely parse a string that may be JSON or a single-quoted Python dict. */
function tryParseLoose(raw: string): Record<string, unknown> | null {
  let text = raw.trim();
  // Strip markdown fences.
  if (text.startsWith("```")) {
    text = text.replace(/^```[a-zA-Z0-9]*\s*/, "");
    if (text.endsWith("```")) text = text.slice(0, -3);
    text = text.trim();
  }
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  const block = start !== -1 && end !== -1 ? text.slice(start, end + 1) : text;
  for (const cand of [block, text, block.replace(/'/g, '"')]) {
    try {
      const parsed = JSON.parse(cand);
      if (parsed && typeof parsed === "object") return parsed as Record<string, unknown>;
    } catch {
      /* try next */
    }
  }
  return null;
}

function asList(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x));
  if (v === null || v === undefined || v === "") return [];
  return [String(v)];
}

/**
 * Normalize an AiReport for display. Defends against a `summary` field that is
 * actually a serialized JSON/dict blob (legacy data) by parsing it; if that
 * fails, surfaces a clean error instead of ever showing raw JSON.
 */
function normalize(report: AiReport): Normalized {
  let summary = (report.summary ?? "").toString();
  let riskScore = report.risk_score;
  let riskLevel = report.risk_level;
  let keyFindings = asList(report.key_findings);
  let recommendedActions = asList(report.recommended_actions);
  let securityObservations = asList(report.security_observations);
  let performanceObservations = asList(report.performance_observations);

  if (summary.trim().startsWith("{")) {
    const parsed = tryParseLoose(summary);
    if (!parsed) {
      return {
        summary: "Report format error - please regenerate",
        riskScore,
        riskLevel,
        keyFindings: [],
        recommendedActions: [],
        securityObservations: [],
        performanceObservations: [],
        ok: false,
      };
    }
    summary = String(parsed.summary ?? "").trim() || "No summary provided.";
    if (parsed.risk_score !== undefined) riskScore = Number(parsed.risk_score);
    if (parsed.risk_level !== undefined) riskLevel = String(parsed.risk_level);
    if (parsed.key_findings !== undefined) keyFindings = asList(parsed.key_findings);
    if (parsed.recommended_actions !== undefined) recommendedActions = asList(parsed.recommended_actions);
    if (parsed.security_observations !== undefined) securityObservations = asList(parsed.security_observations);
    if (parsed.performance_observations !== undefined) performanceObservations = asList(parsed.performance_observations);
  }

  return {
    summary,
    riskScore,
    riskLevel,
    keyFindings,
    recommendedActions,
    securityObservations,
    performanceObservations,
    ok: true,
  };
}

function riskWord(level: string | null, score: number | null): string {
  if (level) return level.toUpperCase();
  if (score === null) return "UNKNOWN";
  return score >= 7 ? "CRITICAL" : score >= 4 ? "WARNING" : "HEALTHY";
}

function Heading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-2 border-l-[3px] border-[#3b82f6] pl-3 text-base font-bold text-white">
      {children}
    </h3>
  );
}

interface Props {
  report: AiReport | null;
  generating?: boolean;
  onGenerate?: () => void;
  onExecuteAction?: (text: string) => void;
  canExecute?: boolean;
}

export function AIReportDisplay({ report, generating, onGenerate, onExecuteAction, canExecute }: Props) {
  // Null / undefined → empty state.
  if (!report) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-[#2d3748] py-12 text-center">
        <BrainCircuit className="h-8 w-8 text-[#64748b]" />
        <p className="text-sm text-[#94a3b8]">No report available yet</p>
        {onGenerate && (
          <Button size="sm" onClick={onGenerate} disabled={generating}>
            {generating && <Loader2 className="h-4 w-4 animate-spin" />} Generate Report
          </Button>
        )}
      </div>
    );
  }

  const n = normalize(report);

  // Parse failure on a JSON-looking summary → clean error, never raw JSON.
  if (!n.ok) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-[#7f1d1d] bg-[#2d1515] py-10 text-center">
        <ShieldAlert className="h-8 w-8 text-[#ef4444]" />
        <p className="text-sm font-medium text-[#fecaca]">Report format error - please regenerate</p>
        {onGenerate && (
          <Button size="sm" onClick={onGenerate} disabled={generating}>
            {generating && <Loader2 className="h-4 w-4 animate-spin" />} Regenerate Report
          </Button>
        )}
      </div>
    );
  }

  const score = n.riskScore ?? null;
  const color = riskColor(score ?? 5);

  return (
    <div className="space-y-6">
      {/* RISK SCORE HERO */}
      <div className="flex flex-col items-center">
        <div
          className="flex items-center justify-center rounded-full"
          style={{ width: 80, height: 80, background: color }}
        >
          <span className="text-[32px] font-bold leading-none text-white">{score ?? "—"}</span>
        </div>
        <div className="mt-2 text-sm font-bold tracking-wide" style={{ color }}>
          {riskWord(n.riskLevel, score)}
        </div>
        <div className="mt-3 h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-[#2d3748]">
          <div className="h-full rounded-full" style={{ width: `${((score ?? 0) / 10) * 100}%`, background: color }} />
        </div>
      </div>

      {/* SUMMARY */}
      <div>
        <Heading>📋 Summary</Heading>
        <div
          className="rounded-lg bg-[#1e2235] p-4 text-[#e2e8f0]"
          style={{ fontSize: 14, lineHeight: 1.7 }}
        >
          {n.summary}
        </div>
      </div>

      {/* KEY FINDINGS */}
      <div>
        <Heading>🔍 Key Findings</Heading>
        {n.keyFindings.length === 0 ? (
          <p className="text-sm text-[#64748b]">No key findings at this time</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-[#2d3748]">
            {n.keyFindings.map((f, i) => (
              <div
                key={i}
                className={`flex items-start gap-3 bg-[#1a1d2e] px-4 py-3 transition-colors hover:bg-[#1e2235] ${i < n.keyFindings.length - 1 ? "border-b border-[#2d3748]" : ""}`}
              >
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#3b82f6] text-xs font-bold text-white">
                  {i + 1}
                </span>
                <span className="text-sm text-[#e2e8f0]">{f}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* RECOMMENDED ACTIONS */}
      <div>
        <Heading>✅ Recommended Actions</Heading>
        {n.recommendedActions.length === 0 ? (
          <p className="text-sm text-[#64748b]">No actions required</p>
        ) : (
          <div className="space-y-2">
            {n.recommendedActions.map((a, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg border-l-[3px] border-[#3b82f6] bg-[#1e2235] px-4 py-3.5"
              >
                <span className="shrink-0 text-2xl font-bold text-[#3b82f6]">{i + 1}</span>
                <span className="flex-1 text-sm text-[#e2e8f0]">{a}</span>
                {onExecuteAction && canExecute && (
                  <Button size="sm" variant="outline" onClick={() => onExecuteAction(a)}>
                    <PlayCircle className="h-3.5 w-3.5" /> Execute
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SECURITY OBSERVATIONS */}
      {n.securityObservations.length > 0 && (
        <div>
          <Heading>🛡️ Security Observations</Heading>
          <div className="space-y-1.5">
            {n.securityObservations.map((o, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 rounded-md border border-[#7f1d1d] bg-[#2d1515] px-3.5 py-2.5"
              >
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-[#ef4444]" />
                <span className="text-sm text-[#e2e8f0]">{o}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* PERFORMANCE OBSERVATIONS */}
      {n.performanceObservations.length > 0 && (
        <div>
          <Heading>⚡ Performance</Heading>
          <div className="space-y-1.5">
            {n.performanceObservations.map((o, i) => (
              <div key={i} className="flex items-start gap-2.5 rounded-md bg-[#1e2235] px-3.5 py-2.5">
                <Zap className="mt-0.5 h-4 w-4 shrink-0 text-[#3b82f6]" />
                <span className="text-sm text-[#e2e8f0]">{o}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* METADATA FOOTER */}
      <div className="border-t border-[#2d3748] pt-3 text-xs text-[#64748b]">
        <div>Report generated: {formatDateTime(report.generated_at)}</div>
        <div>Report type: {report.report_type === "scheduled" ? "Scheduled" : "Manual"}</div>
      </div>
    </div>
  );
}
