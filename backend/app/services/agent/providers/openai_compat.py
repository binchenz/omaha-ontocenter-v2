from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from .base import LLMResponse, Message, ProviderAdapter, ToolCall, ToolSpec, TokenUsage


class OpenAICompatAdapter(ProviderAdapter):
    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        super().__init__(model, api_key, base_url)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def send(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
        }
        if tools:
            kwargs["tools"] = [self._convert_tool(t) for t in tools]
            kwargs["tool_choice"] = tool_choice

        response = await self.client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        result = []
        for m in messages:
            msg: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                msg["content"] = m.content
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id is not None:
                msg["tool_call_id"] = m.tool_call_id
            result.append(msg)
        return result

    def _convert_tool(self, tool: ToolSpec) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": tool.parameters,
                },
            },
        }

    def _parse_response(self, response: Any) -> LLMResponse:
        choice = response.choices[0]
        msg = choice.message

        tool_calls: list[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            usage=usage,
        )
