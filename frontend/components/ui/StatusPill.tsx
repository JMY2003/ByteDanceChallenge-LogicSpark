import clsx from "clsx";

const tones: Record<string, string> = {
  success: "bg-signal/10 text-signal ring-signal/20",
  completed: "bg-signal/10 text-signal ring-signal/20",
  pass: "bg-signal/10 text-signal ring-signal/20",
  running: "bg-signal/10 text-signal ring-signal/20",
  pending: "bg-slate-100 text-steel ring-slate-200",
  failed: "bg-red-50 text-danger ring-red-200",
  needs_revision: "bg-red-50 text-danger ring-red-200",
  pass_with_warnings: "bg-amber-50 text-warn ring-amber-200",
  warning: "bg-amber-50 text-warn ring-amber-200"
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span className={clsx("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1", tones[status] ?? tones.pending)}>
      {status}
    </span>
  );
}
