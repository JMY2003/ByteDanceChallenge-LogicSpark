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

  async function onExport(format: "markdown" | "html" | "json" | "ppt_outline") {
    const exported = await exportReport(projectId, format);
    const blob = new Blob([exported.content], { type: exported.content_type });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = exported.filename;
    anchor.click();
    window.URL.revokeObjectURL(url);
    setMessage(`已下载 ${exported.filename}`);
  }

  return (
    <div className="space-y-4">
      <div className="control-panel flex flex-wrap gap-2">
        <button
          onClick={() => setIsEditing((value) => !value)}
          className="btn"
        >
          <Edit3 size={16} />
          {isEditing ? "预览" : "编辑"}
        </button>
        <button onClick={onSave} className="btn btn-dark">
          <Save size={16} />
          保存
        </button>
        {(["markdown", "html", "json", "ppt_outline"] as const).map((format) => (
          <button
            key={format}
            onClick={() => onExport(format)}
            className="btn"
          >
            <Download size={16} />
            {format === "ppt_outline" ? "PPT 大纲" : format.toUpperCase()}
          </button>
        ))}
      </div>
      {message ? <div className="rounded-lg border border-signal/20 bg-signal/10 p-3 text-sm text-signal">{message}</div> : null}
      {isEditing ? (
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          className="field-control min-h-[720px] p-4 font-mono leading-6"
        />
      ) : (
        <article className="prose-report surface p-6 md:p-8">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </article>
      )}
    </div>
  );
}
