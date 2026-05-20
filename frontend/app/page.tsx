import { CreateProjectForm } from "@/components/CreateProjectForm";
import { MiraBrand } from "@/components/ui/MiraBrand";
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
    <main className="app-page">
      <div className="shell-wide">
        <header className="mx-auto mb-6 max-w-5xl text-center">
          <MiraBrand />
          <h1 className="mt-2 text-4xl font-semibold tracking-normal text-ink md:text-5xl">竞品分析Multi-Agent系统--首页</h1>
          <p className="mx-auto mt-3 max-w-4xl text-balance page-subtitle">
            mira 是一个多 Agent 市场情报研究架构，从任务理解、信息源规划、公开资料采集、Schema 抽取、多维竞品分析、证据链、红队审查到可导出报告，完整模拟一个数字调研小组。
          </p>
        </header>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)] lg:items-stretch">
          <section className="surface-glass home-task-panel p-5 md:p-6 lg:min-h-[745px]">
            <ResearchCockpit />
            <CreateProjectForm />
          </section>
          <ProjectHistoryPanel history={history} />
        </div>
      </div>
    </main>
  );
}

const heroSteps: Array<{ icon: ReactNode; label: string; text: string; tone: string }> = [
  { icon: <GitBranch size={17} />, label: "DAG", text: "任务规划、公开资料采集与自动分析", tone: "bg-[#eef6ff] text-signal ring-[#bad7ff]" },
  { icon: <ShieldCheck size={17} />, label: "Evidence", text: "证据链、引用来源与可信度约束", tone: "bg-[#edf9f5] text-[#0a7f62] ring-[#b7e2d5]" },
  { icon: <Activity size={17} />, label: "Review", text: "红队审查、质量门禁与运行观测", tone: "bg-[#fff7e8] text-[#b56200] ring-[#f2d7a5]" }
];

function ResearchCockpit() {
  return (
    <aside className="mb-6 rounded-lg border border-white/80 bg-white/70 p-4 shadow-hairline backdrop-blur">
      <div className="mb-3">
        <div>
          <div className="eyebrow">Research Cockpit</div>
          <h2 className="mt-1 text-base font-semibold tracking-normal text-ink">从问题到报告的调研链路</h2>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {heroSteps.map((step) => (
          <div key={step.label} className="flex min-h-[88px] items-start gap-3 rounded-lg border border-white/80 bg-white/85 p-3 shadow-hairline">
            <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full ring-1 ${step.tone}`}>{step.icon}</span>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-ink">{step.label}</div>
              <div className="mt-1 text-xs leading-5 text-steel">{step.text}</div>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function ProjectHistoryPanel({ history }: { history: ProjectHistoryItem[] }) {
  return (
    <section className="surface-glass home-history-panel flex max-h-[680px] min-h-0 flex-col p-5 lg:h-[745px] lg:max-h-[745px]">
      <div className="mb-4 flex shrink-0 items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-base font-semibold text-ink">
            <History size={18} className="text-signal" />
            历史记录
          </div>
          <p className="mt-1 text-sm text-steel">仅展示已成功完成的分析任务。</p>
        </div>
        <span className="rounded-full bg-signal/10 px-2.5 py-1 text-xs font-semibold text-signal ring-1 ring-signal/20">{history.length}</span>
      </div>
      {history.length ? (
        <div className="soft-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
          {history.map((project) => (
            <HistoryItem key={project.project_id} project={project} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-line bg-panel px-4 py-8 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-white text-signal shadow-hairline">
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
    <article className="quiet-card transition hover:border-signal/40 hover:bg-white">
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
          className="btn h-9 px-3 text-xs"
        >
          打开工作台
          <ArrowRight size={14} />
        </Link>
        <Link
          href={`/projects/${project.project_id}/report`}
          className="btn h-9 px-3 text-xs"
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
