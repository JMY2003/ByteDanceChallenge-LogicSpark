import { CreateProjectForm } from "@/components/CreateProjectForm";
import { StatusPill } from "@/components/ui/StatusPill";
import { getProjectHistory } from "@/lib/api";
import type { ProjectHistoryItem } from "@/types/api";
import {
  Activity,
  ArrowRight,
  CalendarClock,
  FileText,
  GitBranch,
  History,
  ShieldCheck
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export default async function HomePage() {
  const history = await getProjectHistory().catch(() => []);

  return (
    <main className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
          <div className="flex flex-col gap-3">
            <div className="text-sm font-semibold uppercase tracking-wide text-signal">CompeteScope AI</div>
            <h1 className="max-w-5xl text-5xl font-semibold tracking-normal text-ink">AI 驱动竞品分析 Agent 协作系统</h1>
            <p className="max-w-3xl text-base leading-7 text-steel">
              从任务理解、信息源规划、公开资料采集、Schema 抽取、多维竞品分析、证据链、红队审查到可导出报告，完整模拟一个数字调研小组。
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <Capability icon={<GitBranch size={18} />} title="25 节点 DAG" text="采集、抽取、并行分析、QA、报告写作" />
            <Capability icon={<ShieldCheck size={18} />} title="证据优先" text="事实、推断、建议全部绑定 evidence_ids" />
            <Capability icon={<Activity size={18} />} title="可观测" text="Agent 输入输出、工具调用、质量门禁可追踪" />
          </div>
        </header>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)] lg:items-start">
          <section className="rounded-lg border border-line bg-panel p-6 shadow-soft">
            <CreateProjectForm />
          </section>
          <ProjectHistoryPanel history={history} />
        </div>
      </div>
    </main>
  );
}

function Capability({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
        <span className="text-signal">{icon}</span>
        {title}
      </div>
      <p className="text-sm leading-6 text-steel">{text}</p>
    </div>
  );
}

function ProjectHistoryPanel({ history }: { history: ProjectHistoryItem[] }) {
  return (
    <section className="rounded-lg border border-line bg-white p-5 shadow-soft">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-base font-semibold text-ink">
            <History size={18} className="text-signal" />
            历史记录
          </div>
          <p className="mt-1 text-sm text-steel">仅展示已成功完成的分析任务。</p>
        </div>
        <span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-semibold text-signal ring-1 ring-teal-200">{history.length}</span>
      </div>
      {history.length ? (
        <div className="space-y-3">
          {history.map((project) => (
            <HistoryItem key={project.project_id} project={project} />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-line bg-panel px-4 py-8 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-white text-signal shadow-sm">
            <FileText size={18} />
          </div>
          <p className="text-sm font-medium text-ink">暂无完成记录</p>
          <p className="mt-1 text-sm leading-6 text-steel">任务完整跑完并生成报告后，会自动出现在这里。</p>
        </div>
      )}
    </section>
  );
}

function HistoryItem({ project }: { project: ProjectHistoryItem }) {
  const completedAt = formatDate(project.completed_at);
  const successCount = project.task_counts.success ?? 0;
  const quality = project.quality_score?.total;

  return (
    <article className="rounded-md border border-line bg-panel p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link href={`/projects/${project.project_id}`} className="line-clamp-2 text-sm font-semibold leading-6 text-ink hover:text-signal">
            {project.query}
          </Link>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-steel">
            <span className="inline-flex items-center gap-1">
              <CalendarClock size={13} />
              {completedAt}
            </span>
            <span>{successCount} 个节点成功</span>
            {quality ? <span>质量分 {quality}</span> : null}
          </div>
        </div>
        <StatusPill status={project.status} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Link
          href={`/projects/${project.project_id}`}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-xs font-semibold text-ink hover:border-signal hover:text-signal"
        >
          打开工作台
          <ArrowRight size={14} />
        </Link>
        <Link
          href={`/projects/${project.project_id}/report`}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-xs font-semibold text-ink hover:border-signal hover:text-signal"
        >
          <FileText size={14} />
          查看报告
        </Link>
      </div>
    </article>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}
