import { Database } from "lucide-react";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { getCompetitors } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function KnowledgePage({ params }: PageProps) {
  const { projectId } = await params;
  const competitors = await getCompetitors(projectId);
  return (
    <main className="app-page">
      <div className="shell-wide space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-signal">
              <Database size={16} />
              Knowledge Base
            </div>
            <h1 className="mt-2 page-title">竞品知识库</h1>
          </div>
          <ProjectNav projectId={projectId} />
        </header>
        <section className="grid gap-4 lg:grid-cols-2">
          {competitors.map((competitor) => (
            <article key={competitor.competitor_id} className="surface p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-ink">{competitor.name}</h2>
                  <p className="mt-2 text-sm leading-6 text-steel">{competitor.positioning.short_summary ?? "unknown"}</p>
                </div>
                <span className="rounded-full bg-panel px-2 py-1 text-xs text-steel">{competitor.product_category}</span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <InfoBlock label="目标用户" value={competitor.target_users.join(", ") || "unknown"} />
                <InfoBlock label="商业模式" value={competitor.business_model.join(", ") || "unknown"} />
                <InfoBlock label="来源覆盖" value={(competitor.source_coverage ?? []).join(", ") || "unknown"} />
              </div>
              <div className="mt-4">
                <div className="mb-2 text-sm font-semibold text-ink">功能信号</div>
                <div className="flex flex-wrap gap-2">
                  {competitor.features.map((feature) => (
                    <span key={feature.feature_id} className="rounded-full bg-panel px-2 py-1 text-xs text-steel">
                      {feature.name} · {feature.maturity}
                    </span>
                  ))}
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <SwotColumn title="Strengths" items={competitor.swot?.strengths ?? []} />
                <SwotColumn title="Risks" items={[...(competitor.swot?.weaknesses ?? []), ...(competitor.swot?.threats ?? [])]} />
              </div>
              <div className="mt-4">
                <div className="mb-2 text-sm font-semibold text-ink">价格信号</div>
                {competitor.pricing.length ? (
                  competitor.pricing.map((pricing) => (
                    <div key={`${competitor.competitor_id}-${pricing.plan_name}`} className="rounded-lg bg-panel p-3 text-sm text-steel">
                      {pricing.plan_name}: {pricing.price} · {pricing.billing_cycle}
                    </div>
                  ))
                ) : (
                  <div className="rounded-lg bg-panel p-3 text-sm text-steel">unknown</div>
                )}
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}

function SwotColumn({ title, items }: { title: string; items: Array<{ point?: string; confidence?: number; evidence_ids?: string[] }> }) {
  return (
    <div className="rounded-lg bg-panel p-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-steel">{title}</div>
      {items.length ? (
        <div className="space-y-2">
          {items.slice(0, 3).map((item, index) => (
            <div key={index} className="text-sm leading-6 text-ink">
              {item.point}
              <div className="mt-1 text-xs text-steel">confidence {Number(item.confidence ?? 0).toFixed(2)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-steel">unknown</div>
      )}
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-panel p-3">
      <div className="text-xs font-semibold uppercase tracking-normal text-steel">{label}</div>
      <div className="mt-1 text-sm text-ink">{value}</div>
    </div>
  );
}
