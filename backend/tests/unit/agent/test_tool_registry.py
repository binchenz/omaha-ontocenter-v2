"""Tests for ToolRegistry, ToolContext, and ToolResult."""
import pytest
from app.services.agent.tools.registry import (
    ToolContext,
    ToolResult,
    ToolRegistry,
    global_registry,
    register_tool,
)


# ---------------------------------------------------------------------------
# ToolContext
# ---------------------------------------------------------------------------

def test_tool_context_defaults():
    ctx = ToolContext(db=None, omaha_service=None)
    assert ctx.tenant_id is None
    assert ctx.project_id is None
    assert ctx.session_id is None
    assert ctx.ontology_context == {}
    assert ctx.uploaded_tables == {}


def test_tool_context_full():
    ctx = ToolContext(
        tenant_id=1,
        project_id=2,
        session_id=3,
        db="fake-db",
        omaha_service="fake-svc",
        ontology_context={"key": "val"},
        uploaded_tables={"t": []},
    )
    assert ctx.tenant_id == 1
    assert ctx.project_id == 2
    assert ctx.session_id == 3
    assert ctx.ontology_context == {"key": "val"}
    assert ctx.uploaded_tables == {"t": []}


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------

def test_tool_result_success():
    r = ToolResult(success=True, data={"rows": 5})
    assert r.success is True
    assert r.error is None
    d = r.to_dict()
    assert d["success"] is True
    assert d["data"] == {"rows": 5}
    assert d["error"] is None


def test_tool_result_failure():
    r = ToolResult(success=False, error="something went wrong")
    assert r.success is False
    assert r.data is None
    d = r.to_dict()
    assert d["success"] is False
    assert d["error"] == "something went wrong"


# ---------------------------------------------------------------------------
# ToolRegistry — register & get_specs
# ---------------------------------------------------------------------------

def _make_registry():
    """Return a fresh registry for each test."""
    return ToolRegistry()


def test_register_and_get_specs():
    reg = _make_registry()

    @reg.register("ping", "Ping tool", {"type": "object", "properties": {}})
    async def ping(params, ctx):
        return ToolResult(success=True, data={"pong": True})

    specs = reg.get_specs()
    assert len(specs) == 1
    assert specs[0].name == "ping"
    assert specs[0].description == "Ping tool"


def test_get_specs_whitelist_filters_and_preserves_order():
    reg = _make_registry()

    for name in ("alpha", "beta", "gamma"):
        @reg.register(name, f"{name} tool", {})
        async def handler(params, ctx):
            return ToolResult(success=True)

    # whitelist in reverse order — result should follow whitelist order
    specs = reg.get_specs(whitelist=["gamma", "alpha"])
    assert [s.name for s in specs] == ["gamma", "alpha"]


def test_get_specs_whitelist_ignores_unknown():
    reg = _make_registry()

    @reg.register("only", "only tool", {})
    async def handler(params, ctx):
        return ToolResult(success=True)

    specs = reg.get_specs(whitelist=["only", "nonexistent"])
    assert [s.name for s in specs] == ["only"]


# ---------------------------------------------------------------------------
# ToolRegistry — execute
# ---------------------------------------------------------------------------

async def test_execute_tool():
    reg = _make_registry()

    @reg.register("add", "Add two numbers", {})
    async def add(params, ctx):
        return ToolResult(success=True, data={"sum": params["a"] + params["b"]})

    ctx = ToolContext(db=None, omaha_service=None)
    result = await reg.execute("add", {"a": 2, "b": 3}, ctx)
    assert result.success is True
    assert result.data["sum"] == 5


async def test_execute_unknown_tool():
    reg = _make_registry()
    ctx = ToolContext(db=None, omaha_service=None)
    result = await reg.execute("no_such_tool", {}, ctx)
    assert result.success is False
    assert "no_such_tool" in result.error


async def test_execute_tool_exception_is_caught():
    reg = _make_registry()

    @reg.register("boom", "Exploding tool", {})
    async def boom(params, ctx):
        raise ValueError("kaboom")

    ctx = ToolContext(db=None, omaha_service=None)
    result = await reg.execute("boom", {}, ctx)
    assert result.success is False
    assert "kaboom" in result.error


# ---------------------------------------------------------------------------
# ToolRegistry — has / tool_names
# ---------------------------------------------------------------------------

def test_has_and_tool_names():
    reg = _make_registry()

    @reg.register("x", "x tool", {})
    async def x(params, ctx):
        return ToolResult(success=True)

    assert reg.has("x") is True
    assert reg.has("y") is False
    assert "x" in reg.tool_names


# ---------------------------------------------------------------------------
# get_openai_schemas
# ---------------------------------------------------------------------------

def test_get_openai_schemas_format():
    reg = _make_registry()
    params = {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}

    @reg.register("search", "Search tool", params)
    async def search(params, ctx):
        return ToolResult(success=True)

    schemas = reg.get_openai_schemas()
    assert len(schemas) == 1
    s = schemas[0]
    assert s["type"] == "function"
    assert s["function"]["name"] == "search"
    assert s["function"]["description"] == "Search tool"
    assert s["function"]["parameters"] == params


def test_get_openai_schemas_with_whitelist():
    reg = _make_registry()

    for name in ("a", "b"):
        @reg.register(name, f"{name}", {})
        async def h(params, ctx):
            return ToolResult(success=True)

    schemas = reg.get_openai_schemas(whitelist=["b"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "b"


# ---------------------------------------------------------------------------
# Global singleton & register_tool decorator
# ---------------------------------------------------------------------------

def test_global_register_tool_decorator():
    # Use a unique name to avoid collisions with other tests
    tool_name = "_test_global_ping_unique_xyz"

    @register_tool(tool_name, "Global ping", {})
    async def global_ping(params, ctx):
        return ToolResult(success=True, data={"ok": True})

    assert global_registry.has(tool_name)
    specs = global_registry.get_specs(whitelist=[tool_name])
    assert len(specs) == 1
    assert specs[0].name == tool_name


async def test_global_registry_execute():
    tool_name = "_test_global_exec_unique_xyz"

    @register_tool(tool_name, "Exec test", {})
    async def exec_tool(params, ctx):
        return ToolResult(success=True, data={"done": True})

    ctx = ToolContext(db=None, omaha_service=None)
    result = await global_registry.execute(tool_name, {}, ctx)
    assert result.success is True
    assert result.data["done"] is True
