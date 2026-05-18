"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Database, FileText, GitBranch, Home, ListChecks, type LucideIcon } from "lucide-react";
import clsx from "clsx";

const nav: Array<{ href: string; label: string; icon: LucideIcon; absolute?: boolean }> = [
  { href: "/", label: "首页", icon: Home, absolute: true },
  { href: "", label: "DAG", icon: GitBranch },
  { href: "/knowledge", label: "知识库", icon: Database },
  { href: "/evidence", label: "证据", icon: ListChecks },
  { href: "/report", label: "报告", icon: FileText },
  { href: "/observability", label: "观测", icon: Activity }
];

export function ProjectNav({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-wrap gap-2 rounded-lg border border-line bg-white/75 p-1 shadow-hairline backdrop-blur-xl">
      {nav.map((item) => {
        const Icon = item.icon;
        const href = item.absolute ? item.href : `/projects/${projectId}${item.href}`;
        const active = pathname === href;
        return (
          <Link
            key={item.label}
            href={href}
            className={clsx(
              "inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-medium transition",
              active ? "bg-white text-signal shadow-hairline" : "text-ink hover:bg-white hover:text-signal"
            )}
          >
            <Icon size={16} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
