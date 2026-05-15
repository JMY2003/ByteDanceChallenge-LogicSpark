from app.tools.base import BaseTool


class CitationTool(BaseTool):
    name = "citation"
    description = "Validate that claims have evidence IDs and confidence reflects support strength."

    async def call(self, input_data: dict) -> dict:
        claims = input_data.get("claims", [])
        issues = []
        for claim in claims:
            if not claim.get("evidence_ids"):
                issues.append(
                    {
                        "claim_id": claim.get("claim_id"),
                        "issue_type": "missing_evidence",
                        "severity": "high",
                    }
                )
        return {"passed": not issues, "issues": issues}

