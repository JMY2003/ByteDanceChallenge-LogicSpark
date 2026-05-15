import { CreateProjectForm } from "@/components/CreateProjectForm";
import { Activity, GitBranch, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

export default function HomePage() {
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
        <section className="rounded-lg border border-line bg-panel p-6 shadow-soft">
          <CreateProjectForm />
        </section>
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
