import json

import markdown as markdown_lib

from app.tools.base import BaseTool


class ReportRenderTool(BaseTool):
    name = "report_renderer"
    description = "Render reports as Markdown, HTML and JSON."

    async def call(self, input_data: dict) -> dict:
        markdown = input_data.get("markdown", "")
        json_report = input_data.get("json_report", {})
        html_body = markdown_lib.markdown(markdown, extensions=["tables", "toc"])
        html = (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>CompeteScope AI Report</title>"
            "<style>body{font-family:Inter,Arial,sans-serif;max-width:980px;margin:40px auto;line-height:1.6;color:#17202a}"
            "table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #d7dde5;padding:8px}"
            "code{background:#eef2f7;padding:2px 4px;border-radius:4px}</style></head><body>"
            f"{html_body}</body></html>"
        )
        return {
            "markdown": markdown,
            "html": html,
            "json": json.dumps(json_report, ensure_ascii=False, indent=2),
        }

