import { AgentRunList } from "@/components/agent-trace/AgentRunList";
import { DAGFlow } from "@/components/dag/DAGFlow";
import { ProjectAutoRunner } from "@/components/ProjectAutoRunner";
import { FeatureCoverageChart } from "@/components/report/FeatureCoverageChart";
import { InsightRail } from "@/components/report/InsightRail";
import { QualityPanel } from "@/components/report/QualityPanel";
import { MetricCard } from "@/components/ui/MetricCard";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { StatusPill } from "@/components/ui/StatusPill";
import { getAgentRuns, getDag, getEvidence, getProjectStatus, getReport } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string }>;
  searchParams?: Promise<{ autorun?: string }>;
};

export default async function ProjectRunPage({ params, searchParams }: PageProps) {
  const { projectId } = await params;
  const queryParams = searchParams ? await searchParams : {};
  const [status, dag, runs, evidence, report] = await Promise.all([getProjectStatus(projectId), getDag(projectId), getAgentRuns(projectId), getEvidence(projectId), getReport(projectId).catch(() => null)]);
  const completed = status.task_counts.success ?? 0;
  const failed = status.task_counts.failed ?? 0;
  const pending = status.task_counts.pending ?? 0;
  const toolCalls = runs.reduce((sum, run) => sum + run.tool_calls.length, 0);
  const totalDuration = runs.reduce((sum, run) => sum + run.duration_ms, 0);

  return (
    <main className="min-h-screen px-6 py-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-signal">Project {projectId}</div>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <h1 className="text-3xl font-semibold text-ink">竞品情报工作台</h1>
                <StatusPill status={status.status} />
              </div>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-steel">{status.query}</p>
            </div>
            <div className="flex flex-col items-end gap-3">
              <ProjectNav projectId={projectId} />
              <ProjectAutoRunner projectId={projectId} autoRun={queryParams.autorun === "1"} initialStatus={status.status} />
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-6">
            <MetricCard label="完成节点" value={completed} tone="good" />
            <MetricCard label="等待节点" value={pending} />
            <MetricCard label="失败节点" value={failed} tone={failed ? "danger" : "default"} />
            <MetricCard label="证据数" value={evidence.length} />
            <MetricCard label="工具调用" value={toolCalls} />
            <MetricCard label="耗时" value={`${totalDuration}ms`} />
          </div>
        </header>
        <section className="space-y-5">
          <DAGFlow dag={dag} />
          <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-ink">Agent 执行日志</h2>
              <AgentRunList runs={runs} />
            </section>
            <div className="space-y-5">
              {report?.quality_score ? <QualityPanel score={report.quality_score} /> : null}
              <FeatureCoverageChart report={report?.json_report} />
              <InsightRail report={report?.json_report} />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
