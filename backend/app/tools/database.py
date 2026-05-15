from app.tools.base import BaseTool


class DatabaseTool(BaseTool):
    name = "database"
    description = "Database operations are handled through SQLAlchemy sessions; this tool records intent for observability."

    async def call(self, input_data: dict) -> dict:
        return {"operation": input_data.get("operation", "unknown"), "status": "recorded"}

