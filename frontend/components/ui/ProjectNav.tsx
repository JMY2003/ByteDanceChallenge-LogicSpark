import Link from "next/link";
import { Activity, Database, FileText, GitBranch, Home, ListChecks, type LucideIcon } from "lucide-react";

const nav: Array<{ href: string; label: string; icon: LucideIcon; absolute?: boolean }> = [
  { href: "/", label: "首页", icon: Home, absolute: true },
  { href: "", label: "DAG", icon: GitBranch },
  { href: "/knowledge", label: "知识库", icon: Database },
  { href: "/evidence", label: "证据", icon: ListChecks },
  { href: "/report", label: "报告", icon: FileText },
  { href: "/observability", label: "观测", icon: Activity }
];

export function ProjectNav({ projectId }: { projectId: string }) {
  return (
    <nav className="flex flex-wrap gap-2">
      {nav.map((item) => {
        const Icon = item.icon;
        return (
          <Link
            key={item.label}
            href={item.absolute ? item.href : `/projects/${projectId}${item.href}`}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:border-signal hover:text-signal"
          >
            <Icon size={16} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
