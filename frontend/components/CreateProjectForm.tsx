"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Play, Sparkles, Wand2 } from "lucide-react";
import { createProject } from "@/lib/api";

const examples = [
  "请分析 AI 办公协作领域的竞品，包括 Notion AI、ClickUp AI、Coda AI、飞书、钉钉，并生成产品经理视角报告。",
  "请分析网购协作领域的竞品，包括 京东、阿里巴巴、拼多多、唯品会等平台并生成产品经理视角报告。",
  "分析 LangChain、LlamaIndex、Dify、Flowise、CrewAI、AutoGen 在 AI Agent 开发平台领域的竞争格局。"
];

export function CreateProjectForm() {
  const router = useRouter();
  const [query, setQuery] = useState("请分析 AI 办公协作领域的竞品，包括 Notion AI、ClickUp AI、Coda AI，并生成产品经理视角报告。");
  const [mode, setMode] = useState("quick");
  const [language, setLanguage] = useState("zh-CN");
  const [maxCompetitors, setMaxCompetitors] = useState(6);
  const [deepReview, setDeepReview] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const project = await createProject({
        query,
        mode,
        language,
        output_formats: ["markdown", "html", "json"],
        max_competitors: maxCompetitors,
        enable_deep_review: deepReview
      });
      router.push(`/projects/${project.project_id}?autorun=1`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <label className="block text-sm font-medium text-ink">分析任务</label>
          <div className="flex flex-wrap gap-2">
            {examples.map((example, index) => (
              <button
                key={example}
                type="button"
                onClick={() => setQuery(example)}
                className="inline-flex h-8 items-center gap-1 rounded-md border border-line bg-white px-2 text-xs font-medium text-steel hover:border-signal hover:text-signal"
              >
                <Wand2 size={13} />
                样例 {index + 1}
              </button>
            ))}
          </div>
        </div>
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="min-h-36 w-full rounded-lg border border-line bg-white p-4 text-sm leading-6 outline-none ring-signal/20 focus:border-signal focus:ring-4"
        />
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        <label className="block text-sm">
          <span className="mb-2 block font-medium text-ink">模式</span>
          <select value={mode} onChange={(event) => setMode(event.target.value)} className="h-11 w-full rounded-md border border-line bg-white px-3">
            <option value="quick">快速分析</option>
            <option value="deep">深度分析</option>
            <option value="product">产品经理视角</option>
            <option value="investment">投资视角</option>
            <option value="technical">技术视角</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-2 block font-medium text-ink">语言</span>
          <select value={language} onChange={(event) => setLanguage(event.target.value)} className="h-11 w-full rounded-md border border-line bg-white px-3">
            <option value="zh-CN">中文</option>
            <option value="en-US">English</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-2 block font-medium text-ink">竞品上限</span>
          <input
            type="number"
            min={1}
            max={20}
            value={maxCompetitors}
            onChange={(event) => setMaxCompetitors(Number(event.target.value))}
            className="h-11 w-full rounded-md border border-line bg-white px-3"
          />
        </label>
        <label className="flex items-end gap-3 rounded-md border border-line bg-white px-3 py-2 text-sm">
          <input type="checkbox" checked={deepReview} onChange={(event) => setDeepReview(event.target.checked)} />
          <span className="pb-1 font-medium text-ink">启用深度审查</span>
        </label>
      </div>
      {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm leading-6 text-danger">{error}</div> : null}
      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex h-11 items-center gap-2 rounded-md bg-ink px-5 text-sm font-semibold text-white hover:bg-signal disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? <Sparkles size={18} className="animate-pulse" /> : <Play size={18} />}
        {isSubmitting ? "Agent 正在运行" : "创建并运行"}
      </button>
    </form>
  );
}
