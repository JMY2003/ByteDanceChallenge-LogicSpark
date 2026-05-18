import { AlertTriangle, CheckCircle2, ShieldQuestion } from "lucide-react";

type InsightRailProps = {
  report: Record<string, unknown> | null | undefined;
};

export function InsightRail({ report }: InsightRailProps) {
  const agentOutputs = getRecord(report?.agent_outputs);
  const qualityPayload = getRecord(getRecord(agentOutputs.quality_gate).payload);
  const warnings = (qualityPayload.warnings as string[] | undefined) ?? [];
  const strategic = (getRecord(getRecord(agentOutputs.strategic_insight).payload).strategic_insights as Array<Record<string, unknown>> | undefined) ?? [];
  const redTeam = (getRecord(getRecord(agentOutputs.red_team).payload).red_team_challenges as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <aside className="space-y-4">
      <section className="surface p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
          <CheckCircle2 size={17} className="text-signal" />
          战略洞察
        </div>
        <div className="space-y-3">
          {strategic.slice(0, 4).map((item, index) => (
            <div key={index} className="rounded-lg bg-panel p-3 text-sm leading-6 text-ink">
              {String(item.claim ?? "unknown")}
              <div className="mt-2 text-xs text-steel">confidence {Number(item.confidence ?? 0).toFixed(2)}</div>
            </div>
          ))}
          {!strategic.length ? <div className="text-sm text-steel">暂无战略洞察。</div> : null}
        </div>
      </section>
      <section className="surface p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
          <ShieldQuestion size={17} className="text-warn" />
          红队挑战
        </div>
        <div className="space-y-2">
          {redTeam.slice(0, 5).map((item, index) => (
            <div key={index} className="text-sm leading-6 text-steel">
              {String(item.challenge ?? "unknown")}
            </div>
          ))}
          {!redTeam.length ? <div className="text-sm text-steel">暂无高风险挑战。</div> : null}
        </div>
      </section>
      <section className="surface p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
          <AlertTriangle size={17} className="text-warn" />
          质量警告
        </div>
        <div className="space-y-2">
          {warnings.slice(0, 6).map((warning, index) => (
            <div key={index} className="text-sm leading-6 text-steel">
              {warning}
            </div>
          ))}
          {!warnings.length ? <div className="text-sm text-steel">质量门禁未发现阻塞项。</div> : null}
        </div>
      </section>
    </aside>
  );
}

function getRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}
