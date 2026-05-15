from bs4 import BeautifulSoup

from app.tools.base import BaseTool


class DocumentParserTool(BaseTool):
    name = "document_parser"
    description = "Parse HTML, Markdown or plain text into normalized text chunks."

    async def call(self, input_data: dict) -> dict:
        content = input_data.get("content", "")
        content_type = input_data.get("content_type", "text")
        if content_type == "html":
            soup = BeautifulSoup(content, "html.parser")
            content = soup.get_text("\n")
        text = "\n".join(line.strip() for line in content.splitlines() if line.strip())
        return {"text": text}

