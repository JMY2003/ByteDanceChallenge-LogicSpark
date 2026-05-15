import clsx from "clsx";

const tones: Record<string, string> = {
  success: "bg-teal-50 text-signal ring-teal-200",
  completed: "bg-teal-50 text-signal ring-teal-200",
  pass: "bg-teal-50 text-signal ring-teal-200",
  running: "bg-blue-50 text-blue-700 ring-blue-200",
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

