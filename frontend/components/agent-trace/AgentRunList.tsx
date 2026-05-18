import { AlertTriangle, Clock, TerminalSquare, Wrench } from "lucide-react";
import type { AgentRun } from "@/types/api";

export function AgentRunList({ runs }: { runs: AgentRun[] }) {
  if (!runs.length) {
    return <div className="surface p-5 text-sm text-steel">暂无 Agent 执行日志。</div>;
  }
  return (
    <div className="space-y-3">
      {runs.map((run) => {
        const fallbackWarning = getFallbackWarning(run);
        return (
        <article key={run.id} className="surface p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-semibold text-ink">{run.agent_name}</div>
              <div className="mt-1 text-xs text-steel">{run.id}</div>
            </div>
            <div className="flex items-center gap-3 text-sm text-steel">
              <span className="inline-flex items-center gap-1">
                <TerminalSquare size={15} />
                {run.status}
              </span>
              <span className="inline-flex items-center gap-1">
                <Clock size={15} />
                {run.duration_ms}ms
              </span>
              <span className="inline-flex items-center gap-1">
                <Wrench size={15} />
                {run.tool_calls.length}
              </span>
            </div>
          </div>
          {run.error ? <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-danger">{run.error}</div> : null}
          {fallbackWarning ? (
            <div className="mt-3 flex gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm leading-6 text-red-900">
              <AlertTriangle size={17} className="mt-0.5 shrink-0 text-danger" />
              <span>{fallbackWarning}</span>
            </div>
          ) : null}
          <details className="mt-3">
            <summary className="cursor-pointer text-sm font-medium text-signal">查看输入输出</summary>
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              <pre className="max-h-72 overflow-auto rounded-lg bg-panel p-3 text-xs">{JSON.stringify(run.input, null, 2)}</pre>
              <pre className="max-h-72 overflow-auto rounded-lg bg-panel p-3 text-xs">{JSON.stringify(run.output, null, 2)}</pre>
            </div>
          </details>
          {run.tool_calls.length ? (
            <details className="mt-3 rounded-lg bg-panel p-3">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-normal text-steel">
                Tool Calls ({run.tool_calls.length})
              </summary>
              <div className="mt-3 space-y-2">
                {run.tool_calls.map((call, index) => (
                  <details key={`${run.id}-${index}`} className="border-t border-line pt-2 text-xs text-ink first:border-t-0 first:pt-0">
                    <summary className="cursor-pointer">
                      <span className="font-semibold">{String(call.tool_name)}</span>
                      <span className="ml-2 text-steel">{String(call.status)}</span>
                      <span className="ml-2 text-steel">{String(call.output_summary ?? "").slice(0, 180)}</span>
                    </summary>
                    <div className="mt-2 grid gap-2 lg:grid-cols-2">
                      <pre className="max-h-56 overflow-auto rounded-lg bg-white p-3 text-[11px] leading-5 text-ink">
                        {JSON.stringify(call.input ?? {}, null, 2)}
                      </pre>
                      <pre className="max-h-56 overflow-auto rounded-lg bg-white p-3 text-[11px] leading-5 text-ink">
                        {JSON.stringify(
                          {
                            output_summary: call.output_summary ?? "",
                            error: call.error ?? null,
                            started_at: call.started_at ?? null,
                            ended_at: call.ended_at ?? null
                          },
                          null,
                          2
                        )}
                      </pre>
                    </div>
                  </details>
                ))}
              </div>
            </details>
          ) : null}
        </article>
      );
      })}
    </div>
  );
}

function getFallbackWarning(run: AgentRun): string | null {
  const outputText = JSON.stringify(run.output ?? {});
  if (/fallback_reason|llm_used":false|llm_extraction":\{"used":false|llm_synthesis":\{"used":false/i.test(outputText)) {
    return "该 Agent 回退到确定性逻辑，结果只适合调试，不能作为正式分析依据。";
  }
  if (run.tool_calls.some((call) => String(call.status ?? "").toLowerCase() === "failed")) {
    return "该 Agent 存在失败的工具调用，请检查输入输出后再信任结果。";
  }
  return null;
}
