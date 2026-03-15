"""LLM factory for creating LLM instances based on provider."""

import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from omaha.utils.exceptions import AgentError
from omaha.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_llm(provider: str = "openai", temperature: float = 0) -> Any:
    """Create an LLM instance based on provider.

    Args:
        provider: LLM provider name (openai, anthropic, or deepseek)
        temperature: Temperature for generation

    Returns:
        LLM instance

    Raises:
        AgentError: If provider is unsupported or API key is missing
    """
    provider = provider.lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AgentError("OPENAI_API_KEY environment variable not set")

        logger.info("Creating OpenAI LLM", model="gpt-4")
        return ChatOpenAI(
            model="gpt-4",
            temperature=temperature,
            openai_api_key=api_key,
        )

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AgentError("ANTHROPIC_API_KEY environment variable not set")

        logger.info("Creating Anthropic LLM", model="claude-3-sonnet-20240229")
        return ChatAnthropic(
            model="claude-3-sonnet-20240229",
            temperature=temperature,
            anthropic_api_key=api_key,
        )

    elif provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            raise AgentError("DEEPSEEK_API_KEY environment variable not set")

        logger.info("Creating DeepSeek LLM", model=model, base_url=base_url)
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key,
            openai_api_base=base_url,
        )

    else:
        raise AgentError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: openai, anthropic, deepseek"
        )
