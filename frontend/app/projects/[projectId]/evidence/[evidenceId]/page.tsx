import Link from "next/link";
import { ArrowLeft, LinkIcon } from "lucide-react";
import { MiraBrand } from "@/components/ui/MiraBrand";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { getEvidenceItem } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string; evidenceId: string }>;
};

export default async function EvidenceDetailPage({ params }: PageProps) {
  const { projectId, evidenceId } = await params;
  const evidence = await getEvidenceItem(projectId, evidenceId);
  return (
    <main className="app-page">
      <div className="shell-wide mb-5">
        <MiraBrand />
      </div>
      <div className="shell-wide mb-5">
        <header className="project-header-card flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link href={`/projects/${projectId}/evidence`} className="inline-flex items-center gap-2 text-sm font-medium text-signal">
              <ArrowLeft size={16} />
              返回证据列表
            </Link>
            <h1 className="mt-2 page-title">{evidence.source_title || evidence.evidence_id}</h1>
          </div>
          <ProjectNav projectId={projectId} />
        </header>
      </div>
      <div className="shell-wide space-y-5">
        <article className="surface p-6">
          <div className="flex flex-wrap gap-2 text-xs text-steel">
            <span className="rounded-full bg-panel px-2 py-1">{evidence.source_type}</span>
            <span className="rounded-full bg-panel px-2 py-1">可信度 {evidence.credibility_score.toFixed(2)}</span>
            <span className="rounded-full bg-panel px-2 py-1">新鲜度 {evidence.freshness_score.toFixed(2)}</span>
            {evidence.is_potentially_outdated ? <span className="rounded-full bg-amber-50 px-2 py-1 text-warn">需刷新验证</span> : null}
          </div>
          <h2 className="mt-5 text-xl font-semibold text-ink">{evidence.evidence_id}</h2>
          <a href={evidence.source_url} className="mt-2 inline-flex items-center gap-2 text-sm text-signal">
            <LinkIcon size={15} />
            {evidence.source_url}
          </a>
          <div className="mt-5 rounded-lg bg-panel p-4">
            <div className="text-xs font-semibold uppercase tracking-normal text-steel">Quote</div>
            <p className="mt-2 text-sm leading-6 text-ink">{evidence.quote}</p>
          </div>
          <div className="mt-5">
            <div className="text-xs font-semibold uppercase tracking-normal text-steel">Summary</div>
            <p className="mt-2 text-sm leading-6 text-ink">{evidence.summary}</p>
          </div>
          <div className="mt-5">
            <div className="text-xs font-semibold uppercase tracking-normal text-steel">Supports Claims</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {evidence.supports_claim_ids.length ? (
                evidence.supports_claim_ids.map((claimId) => (
                  <span key={claimId} className="rounded-full bg-panel px-2 py-1 text-xs text-steel">
                    {claimId}
                  </span>
                ))
              ) : (
                <span className="text-sm text-steel">暂无 claim 绑定</span>
              )}
            </div>
          </div>
        </article>
      </div>
    </main>
  );
}
