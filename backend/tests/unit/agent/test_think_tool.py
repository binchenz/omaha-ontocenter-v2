import asyncio
from app.services.agent.tools.registry import ToolContext, global_registry
from app.services.agent.tools.builtin import reasoning  # noqa: F401


class TestThinkTool:
    def test_think_is_registered(self):
        assert global_registry.has("think")

    def test_think_returns_success(self):
        ctx = ToolContext(db=None, omaha_service=None)
        result = asyncio.run(
            global_registry.execute("think", {"reasoning": "test plan"}, ctx)
        )
        assert result.success is True
        assert result.data == {"noted": True}

    def test_think_spec_has_required_reasoning(self):
        specs = {s.name: s for s in global_registry.get_specs()}
        spec = specs["think"]
        assert "reasoning" in spec.parameters["properties"]
        assert spec.parameters["required"] == ["reasoning"]
