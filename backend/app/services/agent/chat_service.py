"""Thin ChatServiceV2 — delegates to ExecutorAgent via ConversationRuntime."""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

# Trigger @register_tool decorators
import app.services.agent.tools.builtin.query  # noqa: F401
import app.services.agent.tools.builtin.chart  # noqa: F401
import app.services.agent.tools.builtin.modeling  # noqa: F401
import app.services.agent.tools.builtin.ingestion  # noqa: F401
import app.services.agent.tools.builtin.asset  # noqa: F401
import app.services.agent.tools.builtin.snapshot  # noqa: F401
import app.services.agent.tools.builtin.navigate  # noqa: F401

from app.services.agent.providers.base import ProviderAdapter
from app.services.agent.providers.openai_compat import OpenAICompatAdapter
from app.services.agent.providers.anthropic import AnthropicAdapter
from app.services.agent.tools.registry import global_registry, ToolContext
from app.services.agent.tools.view import ToolRegistryView
from app.services.agent.tools.factory import ObjectTypeToolFactory
from app.services.agent.skills.loader import SkillLoader
from app.services.agent.skills.resolver import SkillResolver
from app.services.agent.runtime.conversation import ConversationRuntime
from app.services.agent.runtime.session import SessionManager
from app.services.agent.runtime import session_store
from app.services.agent.orchestrator.executor import ExecutorAgent
from app.services.ontology.store import OntologyStore

# Backward compatibility — API layer still imports ChatService
from app.services.agent._legacy_chat_service import ChatService  # noqa: F401


class ProviderFactory:
    @staticmethod
    def create() -> ProviderAdapter:
        """Auto-detect provider from env vars."""
        if key := os.getenv("DEEPSEEK_API_KEY"):
            return OpenAICompatAdapter(
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                api_key=key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            )
        if key := os.getenv("OPENAI_API_KEY"):
            return OpenAICompatAdapter(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                api_key=key,
            )
        if key := os.getenv("ANTHROPIC_API_KEY"):
            return AnthropicAdapter(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
                api_key=key,
            )
        raise RuntimeError(
            "No LLM provider configured. Set DEEPSEEK_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY."
        )


class ChatServiceV2:
    def __init__(self, project: Any, db: Session) -> None:
        self.project = project
        self.db = db
        self.tenant_id: int = project.tenant_id or project.owner_id

    async def send_message(self, session_id: int, user_message: str) -> dict[str, Any]:
        # 1. Resolve skill
        setup_stage: str = getattr(self.project, "setup_stage", None) or "idle"
        loader = SkillLoader()
        resolver = SkillResolver(loader)
        skill = resolver.resolve(setup_stage, user_message)

        # 2. Create provider
        provider = ProviderFactory.create()

        # 3. Build ConversationRuntime
        runtime = ConversationRuntime(skill=skill)

        # 4. Load ontology context
        store = OntologyStore(self.db)
        ontology_context = store.get_full_ontology(self.tenant_id)

        # 5. Build system prompt (inserts into runtime.messages)
        runtime.build_system_prompt(ontology_context)

        # 6. Load chat history and append to runtime
        history = SessionManager.load_history(self.db, session_id)
        for msg in history:
            if msg["role"] == "user":
                runtime.append_user_message(msg["content"])
            elif msg["role"] == "assistant":
                runtime.append_assistant_message(content=msg["content"], tool_calls=None)

        # 7. Append current user message
        runtime.append_user_message(user_message)

        # 8. Build derived tool specs from ontology
        derived_specs = ObjectTypeToolFactory().build(ontology_context)

        # 9. Create ToolRegistryView
        tool_view = ToolRegistryView(builtin=global_registry, derived=derived_specs)

        # 10. Build ToolContext with omaha_service
        omaha_service = self._build_omaha_service()
        ctx = ToolContext(
            db=self.db,
            omaha_service=omaha_service,
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            session_id=session_id,
            ontology_context=ontology_context,
            session_store=session_store,
        )

        # 11. Run ExecutorAgent with tool_view
        executor = ExecutorAgent(provider=provider, registry=tool_view)
        response = await executor.run(runtime, ctx)

        # 12. Save messages
        SessionManager.save_messages(
            self.db,
            session_id,
            user_message,
            response.message,
            chart_config=response.chart_config,
        )

        # 13. Return response dict
        return {
            "message": response.message,
            "tool_calls": response.tool_calls,
            "data_table": response.data_table,
            "chart_config": response.chart_config,
            "sql": response.sql,
            "setup_stage": setup_stage,
            "structured": response.structured,
        }

    def _build_omaha_service(self):
        """Build OmahaService from project.omaha_config if available."""
        config_yaml = getattr(self.project, "omaha_config", None)
        if not config_yaml:
            return None
        try:
            from app.services.legacy.financial.omaha import OmahaService
            return OmahaService(config_yaml)
        except Exception:
            return None
