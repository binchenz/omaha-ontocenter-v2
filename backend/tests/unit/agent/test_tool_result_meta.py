from app.services.agent.tools.registry import ToolResult


class TestToolResultMeta:
    def test_to_dict_without_meta(self):
        r = ToolResult(success=True, data={"x": 1})
        assert r.to_dict() == {"success": True, "data": {"x": 1}, "error": None}

    def test_to_dict_with_meta(self):
        r = ToolResult(
            success=True,
            data={"rows": [1, 2, 3]},
            meta={"object_type": "order", "row_count": 3},
        )
        d = r.to_dict()
        assert d["meta"] == {"object_type": "order", "row_count": 3}
        assert d["success"] is True

    def test_meta_defaults_to_none(self):
        r = ToolResult(success=True)
        assert r.meta is None
        assert "meta" not in r.to_dict()
