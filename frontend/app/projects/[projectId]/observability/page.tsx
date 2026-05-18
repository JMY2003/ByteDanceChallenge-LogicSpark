import { Activity } from "lucide-react";
import { DurationChart } from "@/components/agent-trace/DurationChart";
import { AgentRunList } from "@/components/agent-trace/AgentRunList";
import { MetricCard } from "@/components/ui/MetricCard";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { getAgentRuns, getEvidence, getProjectStatus } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function ObservabilityPage({ params }: PageProps) {
  const { projectId } = await params;
  const [status, runs, evidence] = await Promise.all([getProjectStatus(projectId), getAgentRuns(projectId), getEvidence(projectId)]);
  const totalDuration = runs.reduce((sum, run) => sum + run.duration_ms, 0);
  const failedRuns = runs.filter((run) => run.status === "failed").length;
  const chartData = runs.map((run) => ({ name: run.agent_name.replace("Agent", ""), duration: run.duration_ms }));
  return (
    <main className="app-page">
      <div className="shell-wide space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-signal">
              <Activity size={16} />
              Observability
            </div>
            <h1 className="mt-2 page-title">可观测性 Dashboard</h1>
          </div>
          <ProjectNav projectId={projectId} />
        </header>
        <div className="grid gap-3 md:grid-cols-5">
          <MetricCard label="项目状态" value={status.status} tone={status.status === "completed" ? "good" : "default"} />
          <MetricCard label="Agent Runs" value={runs.length} />
          <MetricCard label="失败数" value={failedRuns} tone={failedRuns ? "danger" : "good"} />
          <MetricCard label="总耗时" value={`${totalDuration}ms`} />
          <MetricCard label="证据数" value={evidence.length} />
        </div>
        <section className="surface p-5">
          <h2 className="mb-4 text-xl font-semibold text-ink">Agent 耗时</h2>
          <DurationChart data={chartData} />
        </section>
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-ink">Trace 明细</h2>
          <AgentRunList runs={runs} />
        </section>
      </div>
    </main>
  );
}
