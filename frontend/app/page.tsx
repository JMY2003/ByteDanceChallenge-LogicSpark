import { CreateProjectForm } from "@/components/CreateProjectForm";

export default function HomePage() {
  return (
    <main className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-3">
          <div className="text-sm font-semibold uppercase tracking-wide text-signal">CompeteScope AI</div>
          <h1 className="text-4xl font-semibold tracking-normal text-ink">AI 驱动竞品分析 Agent 协作系统</h1>
          <p className="max-w-3xl text-base leading-7 text-steel">
            输入一个行业、产品方向或竞品列表，系统会运行 DAG Agent 流程，生成结构化知识库、证据链和可导出的竞品报告。
          </p>
        </header>
        <section className="rounded-lg border border-line bg-panel p-6 shadow-soft">
          <CreateProjectForm />
        </section>
      </div>
    </main>
  );
}

