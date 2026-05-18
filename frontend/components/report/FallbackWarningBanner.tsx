import { AlertTriangle } from "lucide-react";

export function FallbackWarningBanner({ report }: { report: Record<string, unknown> | null | undefined }) {
  const warnings = runtimeWarnings(report);
  if (!warnings.length) {
    return null;
  }

  return (
    <section className="rounded-lg border border-red-300 bg-red-50 p-4 shadow-hairline">
      <div className="flex gap-3">
        <AlertTriangle size={22} className="mt-0.5 shrink-0 text-danger" />
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-danger">本次运行发生 LLM fallback</h2>
          <p className="mt-1 text-sm leading-6 text-red-900">
            下面这些环节没有完成真实 LLM 调用，系统已回退到确定性逻辑。fallback 结果只能用于排查流程，不能作为正式竞品分析结论使用。
          </p>
          <ul className="mt-3 space-y-1 text-sm leading-6 text-red-950">
            {warnings.slice(0, 6).map((warning, index) => (
              <li key={index}>- {warning}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function runtimeWarnings(report: Record<string, unknown> | null | undefined): string[] {
  const warnings = report?.runtime_warnings;
  if (Array.isArray(warnings)) {
    return warnings.map((warning) => String(warning)).filter(Boolean);
  }
  return [];
}
