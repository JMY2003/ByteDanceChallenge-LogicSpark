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
        "rounded-lg border p-4 shadow-hairline backdrop-blur-sm",
        tone === "good" && "border-[#b7e2d5] bg-[#edf9f5]",
        tone === "warn" && "border-[#f2d7a5] bg-[#fff7e8]",
        tone === "danger" && "border-red-200 bg-red-50",
        tone === "default" && "border-line bg-white/80"
      )}
    >
      <div className="text-xs font-medium uppercase tracking-normal text-steel">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-normal text-ink">{value}</div>
    </div>
  );
}
