from __future__ import annotations

from typing import Any, Optional, List, Dict, Union

try:
    import anthropic as anthropic_sdk
except ImportError:
    anthropic_sdk = None

from .base import LLMResponse, Message, ProviderAdapter, ToolCall, ToolSpec, TokenUsage


class AnthropicAdapter(ProviderAdapter):
    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic_sdk.AsyncAnthropic(**kwargs)

    async def send(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        system, converted = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": converted,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [self._convert_tool(t) for t in tools]
            kwargs["tool_choice"] = {"type": tool_choice}

        response = await self.client.messages.create(**kwargs)
        return self._parse_response(response)

    def _convert_messages(self, messages: list[Message]) -> tuple[str | None, list[dict]]:
        system: Optional[str] = None
        result: list[dict] = []

        for m in messages:
            if m.role == "system":
                system = m.content
                continue

            if m.role == "tool":
                # Tool result — wrap in user message with tool_result content block
                result.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.tool_call_id,
                            "content": m.content or "",
                        }
                    ],
                })
                continue

            if m.role == "assistant" and m.tool_calls:
                # Assistant message with tool calls — use content blocks
                content_blocks: list[dict] = []
                if m.content:
                    content_blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                result.append({"role": "assistant", "content": content_blocks})
                continue

            result.append({"role": m.role, "content": m.content or ""})

        return system, result

    def _convert_tool(self, tool: ToolSpec) -> dict:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": {
                "type": "object",
                "properties": tool.parameters,
            },
        }

    def _parse_response(self, response: Any) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        content = "".join(text_parts) if text_parts else None
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return LLMResponse(content=content, tool_calls=tool_calls, usage=usage)
