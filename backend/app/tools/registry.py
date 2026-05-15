from app.tools.base import ToolRegistry
from app.tools.browser import BrowserRenderTool
from app.tools.chart import ChartTool
from app.tools.citation import CitationTool
from app.tools.crawler import WebCrawlerTool
from app.tools.database import DatabaseTool
from app.tools.document_parser import DocumentParserTool
from app.tools.report_renderer import ReportRenderTool
from app.tools.vector_search import VectorSearchTool
from app.tools.web_search import WebSearchTool


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in [
        WebSearchTool(),
        WebCrawlerTool(),
        BrowserRenderTool(),
        DocumentParserTool(),
        VectorSearchTool(),
        DatabaseTool(),
        CitationTool(),
        ReportRenderTool(),
        ChartTool(),
    ]:
        registry.register(tool)
    return registry

