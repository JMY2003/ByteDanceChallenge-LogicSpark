from app.tools.base import BaseTool


class VectorSearchTool(BaseTool):
    name = "vector_search"
    description = "MVP lexical vector-store substitute; production can back this with Qdrant or pgvector."

    async def call(self, input_data: dict) -> dict:
        query = input_data.get("query", "").lower()
        documents = input_data.get("documents", [])
        scored = []
        for doc in documents:
            text = doc.get("text", "").lower()
            score = sum(1 for token in query.split() if token in text)
            if score:
                scored.append({**doc, "score": float(score)})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return {"matches": scored[: int(input_data.get("top_k", 5))]}

