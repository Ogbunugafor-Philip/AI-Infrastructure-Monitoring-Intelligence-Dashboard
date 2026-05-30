"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { colorForIndex, formatClock } from "@/lib/format";
import { EmptyState } from "@/components/EmptyState";
import { Activity } from "lucide-react";

export interface SeriesMeta {
  key: string; // dataKey in the merged rows
  name: string; // legend label
}

interface Props {
  title: string;
  unit?: string;
  rows: Record<string, number | string | null>[]; // merged by timestamp
  series: SeriesMeta[];
}

/** Line chart plotting one metric for multiple servers on a shared time axis. */
export function MultiServerChart({ title, unit = "%", rows, series }: Props) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <h3 className="mb-4 text-sm font-semibold text-slate-200">{title}</h3>
      {rows.length === 0 || series.length === 0 ? (
        <EmptyState
          title="No metric data yet"
          description="Refresh a server to start collecting time-series data."
          icon={<Activity className="h-6 w-6" />}
        />
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={rows} margin={{ top: 5, right: 16, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="time"
              tickFormatter={(v) => formatClock(String(v))}
              stroke="#64748b"
              fontSize={11}
            />
            <YAxis domain={[0, 100]} stroke="#64748b" fontSize={11} unit={unit} />
            <Tooltip
              contentStyle={{
                background: "#0f172a",
                border: "1px solid #1e293b",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelFormatter={(v) => formatClock(String(v))}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {series.map((s, i) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                stroke={colorForIndex(i)}
                dot={false}
                strokeWidth={2}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
