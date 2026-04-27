"""Validate all registered tool schemas are OpenAI strict-mode compliant.

OpenAI rejects array `items` of type \"object\" without explicit `properties`
or `additionalProperties`. This test guards against that regression.
"""
import app.services.agent.tools.builtin  # noqa: F401  ensure tools are registered
from app.services.agent.tools.registry import global_registry


def _walk(node, path="$"):
    if isinstance(node, dict):
        if node.get("type") == "array":
            items = node.get("items")
            assert items is not None, f"{path}.items missing"
            if isinstance(items, dict) and items.get("type") == "object":
                assert (
                    "properties" in items or "additionalProperties" in items
                ), f"{path}.items is bare object — OpenAI will reject"
        for k, v in node.items():
            _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, f"{path}[{i}]")


def test_all_tool_schemas_openai_compliant():
    specs = global_registry.get_specs()
    assert specs, "no tools registered"
    for spec in specs:
        _walk(spec.parameters, path=f"{spec.name}.parameters")
