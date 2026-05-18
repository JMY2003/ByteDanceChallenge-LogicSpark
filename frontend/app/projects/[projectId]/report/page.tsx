import { FileText } from "lucide-react";
import { FallbackWarningBanner } from "@/components/report/FallbackWarningBanner";
import { FeatureCoverageChart } from "@/components/report/FeatureCoverageChart";
import { InsightRail } from "@/components/report/InsightRail";
import { QualityPanel } from "@/components/report/QualityPanel";
import { ReportViewer } from "@/components/report/ReportViewer";
import { SourceMixChart } from "@/components/report/SourceMixChart";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { getReport } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function ReportPage({ params }: PageProps) {
  const { projectId } = await params;
  const report = await getReport(projectId);
  return (
    <main className="app-page">
      <div className="shell-readable space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-signal">
              <FileText size={16} />
              Report
            </div>
            <h1 className="mt-2 page-title">最终报告</h1>
          </div>
          <ProjectNav projectId={projectId} />
        </header>
        <FallbackWarningBanner report={report.json_report} />
        <section className="grid gap-5 xl:grid-cols-[1fr_320px]">
          <div>
            {report.markdown ? (
              <ReportViewer projectId={projectId} markdown={report.markdown} />
            ) : (
              <div className="surface p-5 text-sm text-steel">暂无报告，请先运行项目。</div>
            )}
          </div>
          <div className="space-y-5">
            {report.quality_score ? <QualityPanel score={report.quality_score} /> : null}
            <FeatureCoverageChart report={report.json_report} />
            <SourceMixChart report={report.json_report} />
            <InsightRail report={report.json_report} />
          </div>
        </section>
      </div>
    </main>
  );
}
