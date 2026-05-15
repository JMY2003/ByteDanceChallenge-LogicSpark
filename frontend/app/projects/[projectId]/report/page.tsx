import { FileText } from "lucide-react";
import { ReportViewer } from "@/components/report/ReportViewer";
import { MetricCard } from "@/components/ui/MetricCard";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { getReport } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function ReportPage({ params }: PageProps) {
  const { projectId } = await params;
  const report = await getReport(projectId);
  return (
    <main className="min-h-screen px-6 py-6">
      <div className="mx-auto max-w-6xl space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-signal">
              <FileText size={16} />
              Report
            </div>
            <h1 className="mt-2 text-3xl font-semibold text-ink">最终报告</h1>
          </div>
          <ProjectNav projectId={projectId} />
        </header>
        {report.quality_score ? (
          <div className="grid gap-3 md:grid-cols-4">
            <MetricCard label="总分" value={`${report.quality_score.total}/100`} tone="good" />
            <MetricCard label="覆盖度" value={`${report.quality_score.coverage}/20`} />
            <MetricCard label="证据充分性" value={`${report.quality_score.evidence_strength}/20`} />
            <MetricCard label="引用准确性" value={`${report.quality_score.citation_accuracy}/15`} />
          </div>
        ) : null}
        {report.markdown ? (
          <ReportViewer projectId={projectId} markdown={report.markdown} />
        ) : (
          <div className="rounded-lg border border-line bg-white p-5 text-sm text-steel">暂无报告，请先运行项目。</div>
        )}
      </div>
    </main>
  );
}

