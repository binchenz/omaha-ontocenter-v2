"""Thin ChatServiceV2 — delegates to ExecutorAgent via ConversationRuntime."""
from __future__ import annotations

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
import app.services.agent.tools.builtin.reasoning  # noqa: F401

from app.config import settings
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

_skill_loader = SkillLoader()


class ProviderFactory:
    @staticmethod
    def create() -> ProviderAdapter:
        if settings.DEEPSEEK_API_KEY:
            return OpenAICompatAdapter(
                model=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL + "/v1",
            )
        if settings.OPENAI_API_KEY:
            return OpenAICompatAdapter(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
            )
        if settings.ANTHROPIC_API_KEY:
            return AnthropicAdapter(
                model="claude-3-5-haiku-20241022",
                api_key=settings.ANTHROPIC_API_KEY,
            )
        raise RuntimeError(
            "No LLM provider configured. Set DEEPSEEK_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY."
        )


class ChatServiceV2:
    def __init__(self, project: Any, db: Session) -> None:
        self.project = project
        self.db = db
        self.tenant_id: int = project.tenant_id or project.owner_id

    async def send_message(
        self,
        session_id: int,
        user_message: str,
        uploaded_tables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        setup_stage: str = getattr(self.project, "setup_stage", None) or "idle"
        resolver = SkillResolver(_skill_loader)
        skill = resolver.resolve(setup_stage, user_message)

        provider = ProviderFactory.create()
        runtime = ConversationRuntime(skill=skill)

        store = OntologyStore(self.db)
        ontology_context = store.get_full_ontology(self.tenant_id)
        runtime.build_system_prompt(ontology_context)

        history = SessionManager.load_history(self.db, session_id)
        for msg in history:
            if msg["role"] == "user":
                runtime.append_user_message(msg["content"])
            elif msg["role"] == "assistant":
                runtime.append_assistant_message(content=msg["content"], tool_calls=None)

        runtime.append_user_message(user_message)

        derived_specs = ObjectTypeToolFactory().build(ontology_context)
        tool_view = ToolRegistryView(builtin=global_registry, derived=derived_specs)

        query_engine = self._build_query_engine()
        ctx = ToolContext(
            db=self.db,
            omaha_service=query_engine,
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            session_id=session_id,
            ontology_context=ontology_context,
            uploaded_tables=uploaded_tables or {},
            session_store=session_store,
        )

        executor = ExecutorAgent(provider=provider, registry=tool_view, max_iterations=12)
        response = await executor.run(runtime, ctx)

        SessionManager.save_messages(
            self.db,
            session_id,
            user_message,
            response.message,
            chart_config=response.chart_config,
        )

        return {
            "message": response.message,
            "tool_calls": response.tool_calls,
            "data_table": response.data_table,
            "chart_config": response.chart_config,
            "sql": response.sql,
            "setup_stage": setup_stage,
            "structured": response.structured,
        }

    def _build_query_engine(self):
        config_yaml = getattr(self.project, "omaha_config", None)
        if not config_yaml:
            return None
        try:
            from app.services.query.engine import QueryEngine
            return QueryEngine(config_yaml)
        except Exception:
            return None
