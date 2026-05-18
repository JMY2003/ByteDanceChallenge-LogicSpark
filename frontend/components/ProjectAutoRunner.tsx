"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Play, RefreshCw } from "lucide-react";
import { runProject } from "@/lib/api";

export function ProjectAutoRunner({ projectId, autoRun, initialStatus }: { projectId: string; autoRun: boolean; initialStatus: string }) {
  const router = useRouter();
  const started = useRef(false);
  const [isRunning, setIsRunning] = useState(initialStatus === "running");
  const [error, setError] = useState<string | null>(null);

  const startRun = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setError(null);
    try {
      await runProject(projectId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "运行失败");
    } finally {
      setIsRunning(false);
      router.refresh();
    }
  }, [isRunning, projectId, router]);

  useEffect(() => {
    if (!autoRun || started.current || ["running", "completed"].includes(initialStatus)) return;
    started.current = true;
    void startRun();
  }, [autoRun, initialStatus, startRun]);

  useEffect(() => {
    if (!isRunning) return;
    const timer = window.setInterval(() => router.refresh(), 1800);
    return () => window.clearInterval(timer);
  }, [isRunning, router]);

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={startRun}
        disabled={isRunning}
        className="btn btn-primary h-9"
      >
        {isRunning ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
        {isRunning ? "Agent 运行中" : "运行 DAG"}
      </button>
      {isRunning ? <span className="text-sm text-steel">工作台会自动刷新进度</span> : null}
      {error ? <span className="text-sm text-danger">{error}</span> : null}
    </div>
  );
}
