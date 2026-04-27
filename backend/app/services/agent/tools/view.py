"""
ToolRegistryView — unified view over builtin and derived tools with wildcard support.
"""
from typing import Any, Optional
from app.services.agent.providers.base import ToolSpec
from app.services.agent.tools.registry import ToolRegistry, ToolContext, ToolResult
from app.services.agent.link.resolver import LinkResolver
from app.services.agent.link.expander import LinkExpander

# Static spec for the session-scoped refine tool
REFINE_OBJECTSET_SPEC = ToolSpec(
    name="refine_objectset",
    description=(
        "在上一次查询结果的基础上追加过滤条件重新查询。"
        "当用户说'它们'、'那些'、'刚才的结果再加个条件'时调用此工具，"
        "而不是从零构造新的 search_* 调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "filters_to_add": {
                "type": "object",
                "description": "与上次查询相同的后缀规则过滤参数（slug/_min/_max/_contains）",
                "additionalProperties": True,
            },
            "limit": {"type": "integer", "description": "最大返回行数"},
        },
        "additionalProperties": False,
    },
)


class ToolRegistryView:
    """
    Unified view over builtin (ToolRegistry) and derived (per-object) tools.

    Supports wildcard matching (e.g., 'search_*') and routes execution to
    appropriate handler (builtin registry or derived query logic).
    """

    def __init__(self, builtin: ToolRegistry, derived: list[ToolSpec]):
        self.builtin = builtin
        self.derived = derived
        self._derived_by_name = {spec.name: spec for spec in derived}
        self.link_resolver = LinkResolver()
        self.link_expander = LinkExpander()

    def get_specs(self, whitelist: Optional[list[str]] = None) -> list[ToolSpec]:
        """
        Get tool specs, expanding wildcards.

        Wildcard rules:
        - 'search_*' matches all derived tools starting with 'search_'
        - 'count_*' matches all derived tools starting with 'count_'
        - 'aggregate_*' matches all derived tools starting with 'aggregate_'
        - Exact names match builtin or derived tools

        Args:
            whitelist: List of tool names or wildcard patterns. None = all tools.

        Returns:
            List of ToolSpec instances matching the whitelist.
        """
        if whitelist is None:
            # Return all builtin + all derived + refine_objectset
            return self.builtin.get_specs() + self.derived + [REFINE_OBJECTSET_SPEC]

        expanded: list[str] = []
        for pattern in whitelist:
            if pattern.endswith("*"):
                # Wildcard: prefix match
                prefix = pattern[:-1]
                # Match builtin
                expanded.extend(
                    name for name in self.builtin.tool_names if name.startswith(prefix)
                )
                # Match derived
                expanded.extend(
                    name for name in self._derived_by_name if name.startswith(prefix)
                )
            else:
                # Exact match
                expanded.append(pattern)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for name in expanded:
            if name not in seen:
                seen.add(name)
                unique.append(name)

        # Collect specs in whitelist order
        result: list[ToolSpec] = []
        for name in unique:
            if name == "refine_objectset":
                result.append(REFINE_OBJECTSET_SPEC)
            elif self.builtin.has(name):
                result.extend(self.builtin.get_specs(whitelist=[name]))
            elif name in self._derived_by_name:
                result.append(self._derived_by_name[name])

        return result

    async def execute(self, name: str, params: dict, ctx: ToolContext) -> ToolResult:
        """
        Execute a tool by name.

        Routes to builtin registry or derived handler based on tool name.

        Args:
            name: Tool name (e.g., 'search_product', 'count_order')
            params: Tool parameters
            ctx: Execution context with omaha_service, ontology_context, etc.

        Returns:
            ToolResult with success/data/error
        """
        if name == "refine_objectset":
            return await self._execute_refine(params, ctx)
        elif self.builtin.has(name):
            return await self.builtin.execute(name, params, ctx)
        elif name in self._derived_by_name:
            return await self._execute_derived(name, params, ctx)
        else:
            return ToolResult(success=False, error=f"Unknown tool: {name}")

    async def _execute_derived(
        self, name: str, params: dict, ctx: ToolContext
    ) -> ToolResult:
        try:
            if name.startswith("search_"):
                obj_slug = name[len("search_"):]
                mode = "search"
            elif name.startswith("count_"):
                obj_slug = name[len("count_"):]
                mode = "count"
            elif name.startswith("aggregate_"):
                obj_slug = name[len("aggregate_"):]
                mode = "aggregate"
            else:
                return ToolResult(
                    success=False, error=f"Invalid derived tool name: {name}"
                )

            ontology = ctx.ontology_context.get("ontology", {})
            objects = ontology.get("objects", [])
            obj_def = next(
                (obj for obj in objects if obj.get("slug") == obj_slug), None
            )
            if not obj_def:
                return ToolResult(
                    success=False, error=f"Object with slug '{obj_slug}' not found"
                )

            object_name = obj_def.get("name")
            if not object_name:
                return ToolResult(
                    success=False, error=f"Object '{obj_slug}' has no name"
                )

            filters = self._build_filters(params, obj_def)

            if mode == "aggregate":
                return await self._execute_aggregate(
                    object_name=object_name,
                    obj_slug=obj_slug,
                    obj_def=obj_def,
                    params=params,
                    filters=filters,
                    ctx=ctx,
                )

            selected_columns = params.get("select")
            limit = params.get("limit")

            result = ctx.omaha_service.query_objects(
                object_type=object_name,
                selected_columns=selected_columns,
                filters=filters,
                limit=limit,
            )

            if not result.get("success"):
                return ToolResult(success=False, error=result.get("error", "Query failed"))

            data = result.get("data", [])
            if data:
                ontology = ctx.ontology_context.get("ontology", {})
                self.link_expander.expand_links(data, object_name, ontology, ctx)
                result["data"] = data

            self._save_objectset(ctx, object_name, obj_slug, filters, selected_columns, limit, data)

            if mode == "count":
                return ToolResult(
                    success=True,
                    data={"count": len(data), "data": data[:10]},
                )
            else:
                return ToolResult(success=True, data=result)

        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    async def _execute_aggregate(
        self,
        object_name: str,
        obj_slug: str,
        obj_def: dict[str, Any],
        params: dict[str, Any],
        filters: list[dict[str, Any]],
        ctx: ToolContext,
    ) -> ToolResult:
        if ctx.omaha_service is None:
            return ToolResult(success=False, error="OmahaService not available")

        group_by_slug = params.get("group_by")
        metric = params.get("metric")
        limit = params.get("limit")
        slug_to_name = self._slug_to_name(obj_def)
        group_field = slug_to_name.get(group_by_slug)
        if not group_field:
            return ToolResult(success=False, error=f"Unknown group_by field: {group_by_slug}")

        result = ctx.omaha_service.query_objects(
            object_type=object_name,
            selected_columns=None,
            filters=filters,
            limit=limit,
        )
        if not result.get("success"):
            return ToolResult(success=False, error=result.get("error", "Query failed"))

        rows = result.get("data", []) or []
        groups: dict[Any, list[dict[str, Any]]] = {}
        for row in rows:
            key = row.get(group_field)
            groups.setdefault(key, []).append(row)

        metric_field = None
        metric_op = None
        if metric != "count":
            metric_slug, metric_op = metric.rsplit("_", 1)
            metric_field = slug_to_name.get(metric_slug)
            if not metric_field:
                return ToolResult(success=False, error=f"Unknown metric field: {metric_slug}")

        output = []
        for key, bucket in groups.items():
            if metric == "count":
                metric_value = len(bucket)
            else:
                values = [row.get(metric_field) for row in bucket if isinstance(row.get(metric_field), (int, float))]
                if not values:
                    metric_value = None
                elif metric_op == "sum":
                    metric_value = sum(values)
                elif metric_op == "avg":
                    metric_value = sum(values) / len(values)
                elif metric_op == "min":
                    metric_value = min(values)
                elif metric_op == "max":
                    metric_value = max(values)
                else:
                    return ToolResult(success=False, error=f"Unknown metric op: {metric_op}")
            output.append({"group_by_value": key, "metric_value": metric_value})

        output.sort(key=lambda item: (item["metric_value"] is None, item["metric_value"]), reverse=True)
        if limit:
            output = output[:limit]

        self._save_objectset(ctx, object_name, obj_slug, filters, None, limit, rows)

        return ToolResult(
            success=True,
            data={"groups": output, "metric": metric, "group_by": group_by_slug},
        )

    async def _execute_refine(self, params: dict, ctx: ToolContext) -> ToolResult:
        """Merge new filters with the last ObjectSet and re-query."""
        if ctx.session_store is None or ctx.session_id is None:
            return ToolResult(success=False, error="No session context for refine_objectset")

        last = ctx.session_store.get_last_objectset(ctx.session_id)
        if not last:
            return ToolResult(
                success=False,
                error="没有上一次查询记录，请先使用 search_* 工具查询后再细化。",
            )

        obj_slug = last["obj_slug"]
        ontology = ctx.ontology_context.get("ontology", {})
        obj_def = next(
            (o for o in ontology.get("objects", []) if o.get("slug") == obj_slug), None
        )
        if not obj_def:
            return ToolResult(success=False, error=f"Object '{obj_slug}' no longer in ontology")

        new_filters = self._build_filters(params.get("filters_to_add") or {}, obj_def)
        merged_filters = list(last.get("filters") or []) + new_filters
        limit = params.get("limit") or last.get("limit")

        try:
            result = ctx.omaha_service.query_objects(
                object_type=last["object_type"],
                selected_columns=last.get("selected"),
                filters=merged_filters,
                limit=limit,
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

        if not result.get("success"):
            return ToolResult(success=False, error=result.get("error", "Query failed"))

        self._save_objectset(ctx, last["object_type"], obj_slug, merged_filters, last.get("selected"), limit, result.get("data", []))
        return ToolResult(success=True, data=result)

    @staticmethod
    def _save_objectset(
        ctx: ToolContext, object_type: str, obj_slug: str,
        filters: list, selected: Optional[list], limit: Optional[int], rows: list,
    ) -> None:
        if ctx.session_store is not None and ctx.session_id is not None:
            ctx.session_store.set_last_objectset(
                ctx.session_id,
                {
                    "object_type": object_type,
                    "obj_slug": obj_slug,
                    "filters": filters,
                    "selected": selected,
                    "limit": limit,
                    "last_rids": [r.get("id") for r in rows[:50] if isinstance(r, dict)],
                },
            )

    @staticmethod
    def _slug_to_name(obj_def: dict[str, Any]) -> dict[str, str]:
        return {prop.get("slug"): prop.get("name") for prop in obj_def.get("properties", [])}

    def _build_filters(
        self, params: dict, obj_def: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Build filter list from tool params using suffix conventions."""
        filters: list[dict[str, Any]] = []
        slug_to_name = self._slug_to_name(obj_def)

        for param_key, param_value in params.items():
            if param_value is None:
                continue

            if param_key in ("select", "sort_by", "limit"):
                continue

            if param_key.endswith("_min"):
                base_slug = param_key[: -len("_min")]
                operator = ">="
            elif param_key.endswith("_max"):
                base_slug = param_key[: -len("_max")]
                operator = "<="
            elif param_key.endswith("_contains"):
                base_slug = param_key[: -len("_contains")]
                operator = "LIKE"
                param_value = f"%{param_value}%"
            else:
                base_slug = param_key
                operator = "="

            field_name = slug_to_name.get(base_slug)
            if not field_name:
                continue

            filters.append(
                {"field": field_name, "operator": operator, "value": param_value}
            )

        return filters


