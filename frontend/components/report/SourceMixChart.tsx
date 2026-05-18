"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type SourceRow = {
  name: string;
  count: number;
};

export function SourceMixChart({ report }: { report: Record<string, unknown> | null | undefined }) {
  const rows = buildRows(report);
  if (!rows.length) {
    return null;
  }

  return (
    <section className="surface p-5">
      <div className="mb-4">
        <div className="text-xs font-semibold uppercase tracking-normal text-steel">Source Mix</div>
        <h2 className="mt-1 text-lg font-semibold text-ink">来源结构</h2>
      </div>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 12, left: 18, bottom: 0 }}>
            <CartesianGrid stroke="#eef2f7" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
            <YAxis dataKey="name" type="category" width={72} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="count" name="证据数" fill="#0071e3" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function buildRows(report: Record<string, unknown> | null | undefined): SourceRow[] {
  const sourceMix = getRecord(report?.source_mix);
  const sourceTypes = getRecord(sourceMix.source_types);
  return Object.entries(sourceTypes)
    .map(([sourceType, count]) => ({
      name: sourceLabel(sourceType),
      count: Number(count) || 0
    }))
    .filter((row) => row.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);
}

function sourceLabel(sourceType: string): string {
  const labels: Record<string, string> = {
    official: "官方",
    pricing: "价格",
    docs: "文档",
    review: "评测",
    news: "新闻",
    changelog: "更新",
    search_snippet: "摘要",
    unverified: "未验证",
    crawl_failed: "失败"
  };
  return labels[sourceType] ?? sourceType;
}

function getRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}
