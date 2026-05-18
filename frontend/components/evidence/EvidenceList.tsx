import Link from "next/link";
import { ExternalLink } from "lucide-react";
import type { EvidenceItem } from "@/types/api";

export function EvidenceList({ projectId, evidence }: { projectId: string; evidence: EvidenceItem[] }) {
  if (!evidence.length) {
    return <div className="surface p-5 text-sm text-steel">暂无证据。运行项目后会在这里显示引用片段。</div>;
  }
  return (
    <div className="grid gap-3">
      {evidence.map((item) => (
        <Link
          key={item.evidence_id}
          href={`/projects/${projectId}/evidence/${item.evidence_id}`}
          className="surface p-4 transition hover:border-signal/40 hover:bg-white"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="font-semibold text-ink">{item.source_title || item.evidence_id}</div>
              <div className="mt-1 text-sm text-steel">{item.publisher ?? item.source_type}</div>
            </div>
            <div className="inline-flex items-center gap-1 text-sm text-signal">
              <ExternalLink size={15} />
              详情
            </div>
          </div>
          <p className="mt-3 text-sm leading-6 text-ink">{item.summary}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-steel">
            <span className="rounded-full bg-panel px-2 py-1">{item.source_type}</span>
            <span className="rounded-full bg-panel px-2 py-1">可信度 {item.credibility_score.toFixed(2)}</span>
            <span className="rounded-full bg-panel px-2 py-1">新鲜度 {item.freshness_score.toFixed(2)}</span>
          </div>
        </Link>
      ))}
    </div>
  );
}
