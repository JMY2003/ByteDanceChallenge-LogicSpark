import type { QualityScore } from "@/types/api";

const rows: Array<[keyof QualityScore, string, number]> = [
  ["coverage", "信息覆盖度", 20],
  ["evidence_strength", "证据充分性", 20],
  ["citation_accuracy", "引用准确性", 15],
  ["analysis_depth", "分析深度", 15],
  ["structure", "结构化程度", 10],
  ["consistency", "逻辑一致性", 10],
  ["readability", "可读性", 5],
  ["novelty", "新颖洞察", 5]
];

export function QualityPanel({ score }: { score: QualityScore }) {
  return (
    <section className="surface p-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-steel">Quality Gate</div>
          <div className="mt-2 text-5xl font-semibold tracking-normal text-ink">{score.total}</div>
        </div>
        <div className="rounded-full bg-signal/10 px-3 py-1 text-sm font-semibold text-signal">/ 100</div>
      </div>
      <div className="mt-5 space-y-3">
        {rows.map(([key, label, max]) => {
          const value = score[key];
          return (
            <div key={key}>
              <div className="mb-1 flex justify-between text-xs text-steel">
                <span>{label}</span>
                <span>
                  {value}/{max}
                </span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-[#eef3f8]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-signal to-[#38bdf8]"
                  style={{ width: `${Math.min(100, (value / max) * 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
