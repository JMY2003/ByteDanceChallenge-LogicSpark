"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, Edit3, Save } from "lucide-react";
import { exportReport, saveReport } from "@/lib/api";

export function ReportViewer({ projectId, markdown }: { projectId: string; markdown: string }) {
  const [content, setContent] = useState(markdown);
  const [isEditing, setIsEditing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function onSave() {
    await saveReport(projectId, content);
    setIsEditing(false);
    setMessage("已保存人工编辑版本");
  }

  async function onExport(format: "markdown" | "html" | "json") {
    const exported = await exportReport(projectId, format);
    setMessage(`已生成 ${exported.filename}，内容可通过 API 获取`);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setIsEditing((value) => !value)}
          className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium hover:border-signal"
        >
          <Edit3 size={16} />
          {isEditing ? "预览" : "编辑"}
        </button>
        <button onClick={onSave} className="inline-flex h-10 items-center gap-2 rounded-md bg-ink px-3 text-sm font-semibold text-white hover:bg-signal">
          <Save size={16} />
          保存
        </button>
        {(["markdown", "html", "json"] as const).map((format) => (
          <button
            key={format}
            onClick={() => onExport(format)}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium hover:border-signal"
          >
            <Download size={16} />
            {format.toUpperCase()}
          </button>
        ))}
      </div>
      {message ? <div className="rounded-md border border-teal-200 bg-teal-50 p-3 text-sm text-signal">{message}</div> : null}
      {isEditing ? (
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          className="min-h-[720px] w-full rounded-lg border border-line bg-white p-4 font-mono text-sm leading-6 outline-none focus:border-signal"
        />
      ) : (
        <article className="prose-report rounded-lg border border-line bg-white p-6 shadow-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </article>
      )}
    </div>
  );
}
