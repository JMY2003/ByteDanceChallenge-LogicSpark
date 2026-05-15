class ObservabilityService:
    def summarize(self, agent_runs: list[dict]) -> dict:
        total = len(agent_runs)
        failed = sum(1 for run in agent_runs if run.get("status") == "failed")
        return {"total_runs": total, "failed_runs": failed, "failure_rate": failed / max(1, total)}

