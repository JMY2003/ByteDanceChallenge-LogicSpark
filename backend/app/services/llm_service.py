class LLMService:
    """LLM gateway placeholder.

    MVP agents are deterministic so tests do not require API keys. Production
    can route model calls through this service while preserving JSON Schema
    validation in BaseAgent.
    """

    async def complete_json(self, prompt: str, schema: dict) -> dict:
        raise NotImplementedError("Configure an LLM provider before using complete_json.")

