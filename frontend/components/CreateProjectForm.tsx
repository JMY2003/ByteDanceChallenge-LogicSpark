"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Play, Search, Sparkles, Users, Wand2, X } from "lucide-react";
import { createProject } from "@/lib/api";

type CompetitorInputMode = "specified" | "discover";

type ExamplePreset = {
  label: string;
  inputMode: CompetitorInputMode;
  category: string;
  competitors?: string[];
  competitorCount?: number;
  notes: string;
  mode?: string;
};

const examples: ExamplePreset[] = [
  {
    label: "6000元笔记本",
    inputMode: "discover",
    category: "6000元价位档笔记本电脑",
    competitorCount: 5,
    notes: "关注性能释放、屏幕素质、续航、散热噪音、售后和性价比。",
    mode: "product"
  },
  {
    label: "AI 办公",
    inputMode: "specified",
    category: "AI 办公协作",
    competitors: ["Notion AI", "ClickUp AI", "Coda AI", "飞书", "钉钉"],
    notes: "生成产品经理视角报告，重点比较知识库、协作文档、自动化和定价。",
    mode: "product"
  },
  {
    label: "Agent 平台",
    inputMode: "specified",
    category: "AI Agent 开发平台",
    competitors: ["LangChain", "LlamaIndex", "Dify", "Flowise", "CrewAI", "AutoGen"],
    notes: "关注开发者生态、可观测性、部署方式、开源活跃度和企业落地能力。",
    mode: "technical"
  }
];

const modeLabels: Record<string, string> = {
  quick: "快速分析",
  deep: "深度分析",
  product: "产品经理视角",
  investment: "投资视角",
  technical: "技术视角"
};

export function CreateProjectForm() {
  const router = useRouter();
  const [inputMode, setInputMode] = useState<CompetitorInputMode>("discover");
  const [category, setCategory] = useState("6000元价位档笔记本电脑");
  const [competitors, setCompetitors] = useState(["联想小新", "华硕无畏", "惠普战66"]);
  const [competitorCount, setCompetitorCount] = useState(5);
  const [notes, setNotes] = useState("关注性能释放、屏幕素质、续航、散热噪音、售后和性价比。");
  const [mode, setMode] = useState("quick");
  const [language, setLanguage] = useState("zh-CN");
  const [deepReview, setDeepReview] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generatedPreview = buildQueryPreview({
    inputMode,
    category,
    competitors,
    competitorCount,
    notes,
    mode
  });

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const task = buildTaskPayload({
        inputMode,
        category,
        competitors,
        competitorCount,
        notes,
        mode
      });
      const project = await createProject({
        query: task.query,
        mode,
        language,
        output_formats: ["markdown", "html", "json"],
        max_competitors: task.maxCompetitors,
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

  function applyExample(example: ExamplePreset) {
    setInputMode(example.inputMode);
    setCategory(example.category);
    setNotes(example.notes);
    if (example.competitors) {
      setCompetitors(padCompetitorInputs(example.competitors));
    }
    if (example.competitorCount) {
      setCompetitorCount(example.competitorCount);
    }
    if (example.mode) {
      setMode(example.mode);
    }
  }

  function updateCompetitor(index: number, value: string) {
    setCompetitors((current) => current.map((item, currentIndex) => (currentIndex === index ? value : item)));
  }

  function addCompetitor() {
    setCompetitors((current) => [...current, ""]);
  }

  function removeCompetitor(index: number) {
    setCompetitors((current) => (current.length <= 2 ? current : current.filter((_, currentIndex) => currentIndex !== index)));
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <label className="block text-sm font-medium text-ink">任务输入</label>
          <div className="flex flex-wrap gap-2">
            {examples.map((example) => (
              <button
                key={example.label}
                type="button"
                onClick={() => applyExample(example)}
                className="inline-flex h-8 items-center gap-1 rounded-md border border-line bg-white px-2 text-xs font-medium text-steel hover:border-signal hover:text-signal"
              >
                <Wand2 size={13} />
                {example.label}
              </button>
            ))}
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => setInputMode("specified")}
            className={inputModeButtonClass(inputMode === "specified")}
          >
            <Users size={16} />
            给定竞品
          </button>
          <button
            type="button"
            onClick={() => setInputMode("discover")}
            className={inputModeButtonClass(inputMode === "discover")}
          >
            <Search size={16} />
            AI 发现竞品
          </button>
        </div>
      </div>

      <label className="block text-sm">
        <span className="mb-2 block font-medium text-ink">品类</span>
        <input
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          placeholder="例如：6000元价位档笔记本电脑"
          className="h-11 w-full rounded-md border border-line bg-white px-3 outline-none ring-signal/20 focus:border-signal focus:ring-4"
        />
      </label>

      {inputMode === "specified" ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <label className="text-sm font-medium text-ink">竞品</label>
            <button
              type="button"
              onClick={addCompetitor}
              className="inline-flex h-8 items-center gap-1 rounded-md border border-line bg-white px-2 text-xs font-semibold text-ink hover:border-signal hover:text-signal"
            >
              <Plus size={14} />
              添加竞品
            </button>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {competitors.map((competitor, index) => (
              <div key={index} className="flex min-w-0 items-center gap-2">
                <input
                  value={competitor}
                  onChange={(event) => updateCompetitor(index, event.target.value)}
                  placeholder={`竞品 ${index + 1}`}
                  className="h-11 min-w-0 flex-1 rounded-md border border-line bg-white px-3 text-sm outline-none ring-signal/20 focus:border-signal focus:ring-4"
                />
                {competitors.length > 2 ? (
                  <button
                    type="button"
                    onClick={() => removeCompetitor(index)}
                    aria-label={`移除竞品 ${index + 1}`}
                    title="移除"
                    className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-line bg-white text-steel hover:border-red-200 hover:text-danger"
                  >
                    <X size={16} />
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <label className="block text-sm md:max-w-xs">
          <span className="mb-2 block font-medium text-ink">竞品数量</span>
          <input
            type="number"
            min={2}
            max={20}
            value={competitorCount}
            onChange={(event) => setCompetitorCount(Number(event.target.value))}
            className="h-11 w-full rounded-md border border-line bg-white px-3 outline-none ring-signal/20 focus:border-signal focus:ring-4"
          />
        </label>
      )}

      <label className="block text-sm">
        <span className="mb-2 block font-medium text-ink">其他说明</span>
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="例如：重点关注价格、功能、用户评价、渠道策略。"
          className="min-h-24 w-full rounded-md border border-line bg-white p-3 leading-6 outline-none ring-signal/20 focus:border-signal focus:ring-4"
        />
      </label>

      <div className="rounded-md border border-dashed border-line bg-white/70 p-3 text-sm leading-6 text-steel">
        <div className="mb-1 font-semibold text-ink">任务预览</div>
        {generatedPreview}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
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

function buildTaskPayload({
  inputMode,
  category,
  competitors,
  competitorCount,
  notes,
  mode
}: {
  inputMode: CompetitorInputMode;
  category: string;
  competitors: string[];
  competitorCount: number;
  notes: string;
  mode: string;
}) {
  const categoryValue = category.trim();
  if (!categoryValue) {
    throw new Error("请填写品类。");
  }

  if (inputMode === "specified") {
    const selectedCompetitors = normalizeCompetitors(competitors);
    if (selectedCompetitors.length < 2) {
      throw new Error("给定竞品模式下至少填写两个竞品。");
    }
    return {
      query: [
        `分析任务：请分析${categoryValue}品类的竞品，包括 ${selectedCompetitors.join("、")}。`,
        normalizeNotes(notes),
        `报告视角：${modeLabels[mode] ?? mode}。`
      ]
        .filter(Boolean)
        .join(""),
      maxCompetitors: selectedCompetitors.length
    };
  }

  const count = normalizeCompetitorCount(competitorCount);
  return {
    query: [
      `分析任务：请分析${categoryValue}品类，由 AI 自动选择 ${count} 个合适竞品。`,
      normalizeNotes(notes),
      `报告视角：${modeLabels[mode] ?? mode}。`
    ]
      .filter(Boolean)
      .join(""),
    maxCompetitors: count
  };
}

function buildQueryPreview(input: {
  inputMode: CompetitorInputMode;
  category: string;
  competitors: string[];
  competitorCount: number;
  notes: string;
  mode: string;
}) {
  try {
    return buildTaskPayload(input).query;
  } catch {
    return "请补全必填项后创建任务。";
  }
}

function normalizeCompetitors(competitors: string[]) {
  return Array.from(new Set(competitors.map((competitor) => competitor.trim()).filter(Boolean))).slice(0, 20);
}

function normalizeCompetitorCount(value: number) {
  if (!Number.isFinite(value)) {
    throw new Error("竞品数量需要是有效数字。");
  }
  if (value < 2) {
    throw new Error("AI 发现竞品模式下竞品数量至少为 2。");
  }
  if (value > 20) {
    throw new Error("竞品数量最多为 20。");
  }
  return Math.trunc(value);
}

function normalizeNotes(value: string) {
  const notes = value.trim();
  if (!notes) {
    return "";
  }
  return `其他说明：${/[。.!！？?]$/.test(notes) ? notes : `${notes}。`}`;
}

function padCompetitorInputs(values: string[]) {
  const nextValues = [...values];
  while (nextValues.length < 3) {
    nextValues.push("");
  }
  return nextValues;
}

function inputModeButtonClass(active: boolean) {
  return [
    "inline-flex h-11 items-center justify-center gap-2 rounded-md border px-3 text-sm font-semibold transition",
    active ? "border-signal bg-teal-50 text-signal" : "border-line bg-white text-steel hover:border-signal hover:text-signal"
  ].join(" ");
}
