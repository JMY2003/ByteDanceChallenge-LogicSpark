"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type ChartRow = {
  name: string;
  supported: number;
  unknown: number;
};

export function FeatureCoverageChart({ report }: { report: Record<string, unknown> | null | undefined }) {
  const rows = buildRows(report);
  if (!rows.length) {
    return null;
  }
  return (
    <section className="surface p-5">
      <div className="mb-4">
        <div className="text-xs font-semibold uppercase tracking-normal text-steel">Feature Coverage</div>
        <h2 className="mt-1 text-lg font-semibold text-ink">功能覆盖对比</h2>
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
            <CartesianGrid stroke="#eef2f7" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="supported" name="支持" stackId="features" fill="#0071e3" radius={[4, 4, 0, 0]} />
            <Bar dataKey="unknown" name="unknown" stackId="features" fill="#d2d2d7" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function buildRows(report: Record<string, unknown> | null | undefined): ChartRow[] {
  const matrix = getRecord(report?.feature_matrix);
  const competitors = new Map<string, ChartRow>();
  Object.values(matrix).forEach((featureValue) => {
    const feature = getRecord(featureValue);
    Object.entries(feature).forEach(([competitor, value]) => {
      const cell = getRecord(value);
      const row = competitors.get(competitor) ?? { name: competitor, supported: 0, unknown: 0 };
      if (cell.support === true) {
        row.supported += 1;
      } else {
        row.unknown += 1;
      }
      competitors.set(competitor, row);
    });
  });
  return Array.from(competitors.values()).slice(0, 8);
}

function getRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}
