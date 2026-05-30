import { usageColorHex } from "@/lib/gauge-color";

interface GaugeProps {
  value: number | null; // 0-100
  label: string;
  size?: number;
}

/** Simple SVG radial gauge with threshold colouring (green/yellow/red). */
export function Gauge({ value, label, size = 96 }: GaugeProps) {
  const clamped = Math.max(0, Math.min(100, value ?? 0));
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const color = usageColorHex(clamped);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} stroke="#1e293b" strokeWidth={8} fill="none" />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={8}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.5s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold text-slate-100">
            {value === null ? "—" : `${clamped.toFixed(0)}%`}
          </span>
        </div>
      </div>
      <span className="text-xs text-slate-400">{label}</span>
    </div>
  );
}
