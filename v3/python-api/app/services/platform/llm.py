"""LLM provider abstraction layer."""

from app.config import settings


class LLMClient:
    """Abstract LLM client supporting multiple providers."""

    def __init__(self):
        self.provider = settings.llm_provider
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url

    async def chat(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict:
        if self.provider == "openai":
            return await self._openai_chat(messages, tools, **kwargs)
        elif self.provider == "anthropic":
            return await self._anthropic_chat(messages, tools, **kwargs)
        elif self.provider in ("ollama", "vllm"):
            return await self._openai_compat_chat(messages, tools, **kwargs)
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def _openai_chat(self, messages: list[dict], tools: list[dict] | None, **kwargs) -> dict:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        params = {"model": kwargs.get("model", "gpt-4o"), "messages": messages}
        if tools:
            params["tools"] = tools
        response = await client.chat.completions.create(**params)
        return response.model_dump()

    async def _anthropic_chat(self, messages: list[dict], tools: list[dict] | None, **kwargs) -> dict:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self.api_key)
        system = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_messages.append(m)
        params = {
            "model": kwargs.get("model", "claude-sonnet-4-6"),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": user_messages,
        }
        if system:
            params["system"] = system
        if tools:
            params["tools"] = tools
        response = await client.messages.create(**params)
        return response.model_dump()

    async def _openai_compat_chat(self, messages: list[dict], tools: list[dict] | None, **kwargs) -> dict:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key or "ollama", base_url=self.base_url)
        params = {"model": kwargs.get("model", "llama3"), "messages": messages}
        response = await client.chat.completions.create(**params)
        return response.model_dump()


llm_client = LLMClient()
