"""
ToolRegistryView — unified view over builtin and derived tools with wildcard support.
"""
from typing import Any
from app.services.agent.providers.base import ToolSpec
from app.services.agent.tools.registry import ToolRegistry, ToolContext, ToolResult


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

    def get_specs(self, whitelist: list[str] | None = None) -> list[ToolSpec]:
        """
        Get tool specs, expanding wildcards.

        Wildcard rules:
        - 'search_*' matches all derived tools starting with 'search_'
        - 'count_*' matches all derived tools starting with 'count_'
        - Exact names match builtin or derived tools

        Args:
            whitelist: List of tool names or wildcard patterns. None = all tools.

        Returns:
            List of ToolSpec instances matching the whitelist.
        """
        if whitelist is None:
            # Return all builtin + all derived
            return self.builtin.get_specs() + self.derived

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
            if self.builtin.has(name):
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
        if self.builtin.has(name):
            return await self.builtin.execute(name, params, ctx)
        elif name in self._derived_by_name:
            return await self._execute_derived(name, params, ctx)
        else:
            return ToolResult(success=False, error=f"Unknown tool: {name}")

    async def _execute_derived(
        self, name: str, params: dict, ctx: ToolContext
    ) -> ToolResult:
        """
        Execute a derived per-object tool (search_* or count_*).

        Parses object slug from tool name, looks up object_name from
        ctx.ontology_context, builds filter list from params, and calls
        ctx.omaha_service.query_objects.

        For count_* tools: returns {count, data[:10]}
        For search_* tools: returns full query result
        """
        try:
            # Parse object slug from tool name
            if name.startswith("search_"):
                obj_slug = name[len("search_") :]
                is_count = False
            elif name.startswith("count_"):
                obj_slug = name[len("count_") :]
                is_count = True
            else:
                return ToolResult(
                    success=False, error=f"Invalid derived tool name: {name}"
                )

            # Look up object_name from ontology_context
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

            # Build filter list from params
            filters = self._build_filters(params, obj_def)

            # Build selected_columns from select param
            selected_columns = params.get("select")

            # Build sort_by (not yet implemented in OmahaService, but prepare)
            # For now, we'll ignore sort_by

            # Build limit
            limit = params.get("limit")

            # Call omaha_service.query_objects
            result = ctx.omaha_service.query_objects(
                object_type=object_name,
                selected_columns=selected_columns,
                filters=filters,
                limit=limit,
            )

            if not result.get("success"):
                return ToolResult(success=False, error=result.get("error", "Query failed"))

            # For count tools, return count + first 10 rows
            if is_count:
                data = result.get("data", [])
                count = len(data)
                return ToolResult(
                    success=True,
                    data={"count": count, "data": data[:10]},
                )
            else:
                return ToolResult(success=True, data=result)

        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def _build_filters(
        self, params: dict, obj_def: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Build filter list from tool params.

        Suffix rules:
        - _min → operator '>='
        - _max → operator '<='
        - _contains → operator 'LIKE'
        - no suffix → operator '='

        Args:
            params: Tool parameters
            obj_def: Object definition with properties

        Returns:
            List of filter dicts: [{"field": "...", "operator": "...", "value": ...}]
        """
        filters: list[dict[str, Any]] = []
        properties = obj_def.get("properties", [])
        slug_to_name = {prop.get("slug"): prop.get("name") for prop in properties}

        for param_key, param_value in params.items():
            if param_value is None:
                continue

            # Skip non-filter params
            if param_key in ("select", "sort_by", "limit"):
                continue

            # Parse suffix
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

            # Look up field name from slug
            field_name = slug_to_name.get(base_slug)
            if not field_name:
                # Skip unknown slugs
                continue

            filters.append(
                {"field": field_name, "operator": operator, "value": param_value}
            )

        return filters


