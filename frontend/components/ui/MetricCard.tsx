import clsx from "clsx";

type MetricCardProps = {
  label: string;
  value: string | number;
  tone?: "default" | "good" | "warn" | "danger";
};

export function MetricCard({ label, value, tone = "default" }: MetricCardProps) {
  return (
    <div
      className={clsx(
        "rounded-lg border bg-white p-4 shadow-sm",
        tone === "good" && "border-teal-200",
        tone === "warn" && "border-amber-200",
        tone === "danger" && "border-red-200",
        tone === "default" && "border-line"
      )}
    >
      <div className="text-xs font-medium uppercase tracking-wide text-steel">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-ink">{value}</div>
    </div>
  );
}

