import { AgentRunList } from "@/components/agent-trace/AgentRunList";
import { DAGFlow } from "@/components/dag/DAGFlow";
import { MetricCard } from "@/components/ui/MetricCard";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { getAgentRuns, getDag, getProjectStatus } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function ProjectRunPage({ params }: PageProps) {
  const { projectId } = await params;
  const [status, dag, runs] = await Promise.all([getProjectStatus(projectId), getDag(projectId), getAgentRuns(projectId)]);
  const completed = status.task_counts.success ?? 0;
  const failed = status.task_counts.failed ?? 0;
  const pending = status.task_counts.pending ?? 0;

  return (
    <main className="min-h-screen px-6 py-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-signal">Project {projectId}</div>
              <h1 className="mt-2 text-3xl font-semibold text-ink">DAG 任务运行图</h1>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-steel">{status.query}</p>
            </div>
            <ProjectNav projectId={projectId} />
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <MetricCard label="项目状态" value={status.status} tone={status.status === "completed" ? "good" : "default"} />
            <MetricCard label="完成节点" value={completed} tone="good" />
            <MetricCard label="等待节点" value={pending} />
            <MetricCard label="失败节点" value={failed} tone={failed ? "danger" : "default"} />
          </div>
        </header>
        <section>
          <DAGFlow dag={dag} />
        </section>
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-ink">Agent 执行日志</h2>
          <AgentRunList runs={runs} />
        </section>
      </div>
    </main>
  );
}

