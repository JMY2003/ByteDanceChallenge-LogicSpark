from app.tools.base import BaseTool


class BrowserRenderTool(BaseTool):
    name = "browser_render"
    description = "Placeholder for compliant dynamic rendering and screenshots."

    async def call(self, input_data: dict) -> dict:
        return {
            "rendered": False,
            "reason": "MVP uses static crawler; production can attach Playwright here.",
            "url": input_data.get("url"),
        }

