"""Agent domain package. Re-exports key symbols for backward compat."""
from app.services.agent.react import format_onboarding_context, SYSTEM_PROMPT_TEMPLATE, ONBOARDING_PROMPTS, AgentService  # noqa: F401
from app.services.agent_tools import AgentToolkit  # noqa: F401 — actual impl in agent_tools.py
from app.services.agent.chart_engine import ChartEngine  # noqa: F401
