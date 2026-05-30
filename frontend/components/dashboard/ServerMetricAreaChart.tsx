"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Point {
  collected_at: string;
  value: number | null;
}

interface Props {
  title: string;
  data: Point[];
  color: string; // hex base color for the line + gradient
  showReferenceLines?: boolean; // 60% warn / 80% critical (CPU & RAM)
}

const HOUR = 3600 * 1000;

function hhmm(t: number): string {
  const d = new Date(t);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function ServerMetricAreaChart({ title, data, color, showReferenceLines }: Props) {
  // Build {t, v} points.
  let rows = data
    .map((p) => ({ t: new Date(p.collected_at).getTime(), v: p.value }))
    .sort((a, b) => a.t - b.t);

  // Single point → flat line across a 24h window so it never shows just a dot.
  if (rows.length === 1) {
    const only = rows[0];
    rows = [{ t: only.t - 24 * HOUR, v: only.v }, { t: only.t, v: only.v }];
  }

  const hasData = rows.length > 0;
  const minT = hasData ? rows[0].t : Date.now() - 24 * HOUR;
  const maxT = hasData ? rows[rows.length - 1].t : Date.now();

  // X ticks every 2 hours across the range.
  const ticks: number[] = [];
  if (hasData) {
    const start = Math.ceil(minT / (2 * HOUR)) * (2 * HOUR);
    for (let t = start; t <= maxT; t += 2 * HOUR) ticks.push(t);
    if (ticks.length === 0) ticks.push(minT, maxT);
  }

  const gradId = `grad-${title.replace(/[^a-z0-9]/gi, "")}`;

  return (
    <div className="rounded-2xl border border-[#2d3748] bg-[#1a1d2e] p-4">
      <h3 className="mb-3 text-sm font-semibold text-[#e2e8f0]">{title}</h3>
      {!hasData ? (
        <div className="flex h-[200px] items-center justify-center text-sm text-[#64748b]">
          No data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={rows} margin={{ top: 6, right: 12, bottom: 4, left: -16 }}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
            <XAxis
              dataKey="t"
              type="number"
              domain={[minT, maxT]}
              ticks={ticks}
              tickFormatter={(t) => hhmm(Number(t))}
              stroke="#64748b"
              fontSize={11}
            />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tickFormatter={(v) => `${v}%`}
              stroke="#64748b"
              fontSize={11}
            />
            <Tooltip
              contentStyle={{
                background: "#1a1d2e",
                border: "1px solid #2d3748",
                borderRadius: 8,
                fontSize: 12,
                color: "#e2e8f0",
              }}
              labelFormatter={(t) => hhmm(Number(t))}
            />
            {showReferenceLines && (
              <>
                <ReferenceLine y={60} stroke="#f59e0b" strokeDasharray="4 4" />
                <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="4 4" />
              </>
            )}
            <Area
              type="monotone"
              dataKey="v"
              name={title.split(" ")[0]}
              unit="%"
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              fill={`url(#${gradId})`}
              connectNulls
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
