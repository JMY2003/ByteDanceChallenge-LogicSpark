from app.tools.base import BaseTool


class ChartTool(BaseTool):
    name = "chart"
    description = "Generate JSON chart payloads for feature matrices and quality dashboards."

    async def call(self, input_data: dict) -> dict:
        chart_type = input_data.get("chart_type", "feature_matrix")
        return {"chart_type": chart_type, "data": input_data.get("data", {})}

