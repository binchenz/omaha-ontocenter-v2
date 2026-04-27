"""
ObjectTypeToolFactory — generates per-object search and count tools from ontology.
"""
from typing import Any
from app.services.agent.providers.base import ToolSpec


class ObjectTypeToolFactory:
    """Factory for building derived query tools from ontology objects."""

    @staticmethod
    def build(ontology: dict[str, Any]) -> list[ToolSpec]:
        """
        Build search_<slug>, count_<slug>, and aggregate_<slug> tools for each object in ontology.

        Args:
            ontology: Dict with 'objects' key containing list of object configs.
                      Each object must have 'name', 'slug', and 'properties'.

        Returns:
            List of ToolSpec instances (search and count for each object).
        """
        tools: list[ToolSpec] = []
        objects = ontology.get("objects", [])

        for obj in objects:
            obj_name = obj.get("name", "")
            obj_slug = obj.get("slug", "")
            if not obj_slug:
                continue

            properties = obj.get("properties", [])

            # Build search tool
            search_params = ObjectTypeToolFactory._build_search_params(
                properties, obj_name
            )
            tools.append(
                ToolSpec(
                    name=f"search_{obj_slug}",
                    description=f"Search {obj_name} objects with filters and sorting",
                    parameters=search_params,
                )
            )

            # Build count tool
            count_params = ObjectTypeToolFactory._build_count_params(
                properties, obj_name
            )
            tools.append(
                ToolSpec(
                    name=f"count_{obj_slug}",
                    description=f"Count {obj_name} ({obj_slug}) objects matching filters",
                    parameters=count_params,
                )
            )

            # Build aggregate tool
            aggregate_params = ObjectTypeToolFactory._build_aggregate_params(
                properties, obj_name
            )
            tools.append(
                ToolSpec(
                    name=f"aggregate_{obj_slug}",
                    description=f"Aggregate {obj_name} ({obj_slug}) by group with count/sum/avg/min/max",
                    parameters=aggregate_params,
                )
            )

        return tools

    @staticmethod
    def _build_search_params(
        properties: list[dict[str, Any]], obj_name: str
    ) -> dict[str, Any]:
        """
        Build flat parameter schema for search tool.

        For each property:
        - Add <slug> param for exact match
        - For numeric types: add <slug>_min and <slug>_max
        - For string types: add <slug>_contains
        Plus: select (array of property slugs), sort_by (enum), limit (int)
        """
        props_dict: dict[str, Any] = {}
        enum_slugs: list[str] = []
        sort_enum: list[str] = []

        for prop in properties:
            prop_name = prop.get("name", "")
            prop_slug = prop.get("slug", "")
            prop_type = prop.get("type", "string")
            description = prop.get("description", "")

            if not prop_slug:
                continue

            enum_slugs.append(prop_slug)
            sort_enum.append(prop_slug)
            sort_enum.append(f"{prop_slug}_desc")

            # Exact match param
            desc_suffix = f" ({prop_name})" if prop_name else ""
            if prop_type in ("integer", "float", "number"):
                props_dict[prop_slug] = {
                    "type": "number",
                    "description": f"Exact match for {description or prop_name}{desc_suffix}",
                }
                # Range params
                props_dict[f"{prop_slug}_min"] = {
                    "type": "number",
                    "description": f"Minimum value for {prop_name}{desc_suffix}",
                }
                props_dict[f"{prop_slug}_max"] = {
                    "type": "number",
                    "description": f"Maximum value for {prop_name}{desc_suffix}",
                }
            else:
                # String type
                props_dict[prop_slug] = {
                    "type": "string",
                    "description": f"Exact match for {description or prop_name}{desc_suffix}",
                }
                props_dict[f"{prop_slug}_contains"] = {
                    "type": "string",
                    "description": f"Substring match for {prop_name}{desc_suffix}",
                }

        # Add select, sort_by, limit
        props_dict["select"] = {
            "type": "array",
            "items": {"type": "string", "enum": enum_slugs},
            "description": "Properties to return (slugs)",
        }
        props_dict["sort_by"] = {
            "type": "string",
            "enum": sort_enum,
            "description": "Sort by property slug or slug_desc for descending",
        }
        props_dict["limit"] = {
            "type": "integer",
            "description": "Maximum number of results",
        }

        return {
            "type": "object",
            "properties": props_dict,
            "additionalProperties": False,
        }

    @staticmethod
    def _build_count_params(
        properties: list[dict[str, Any]], obj_name: str
    ) -> dict[str, Any]:
        """
        Build flat parameter schema for count tool.

        Same filter params as search, but no select/sort_by/limit.
        """
        props_dict: dict[str, Any] = {}

        for prop in properties:
            prop_name = prop.get("name", "")
            prop_slug = prop.get("slug", "")
            prop_type = prop.get("type", "string")
            description = prop.get("description", "")

            if not prop_slug:
                continue

            desc_suffix = f" ({prop_name})" if prop_name else ""
            if prop_type in ("integer", "float", "number"):
                props_dict[prop_slug] = {
                    "type": "number",
                    "description": f"Exact match for {description or prop_name}{desc_suffix}",
                }
                props_dict[f"{prop_slug}_min"] = {
                    "type": "number",
                    "description": f"Minimum value for {prop_name}{desc_suffix}",
                }
                props_dict[f"{prop_slug}_max"] = {
                    "type": "number",
                    "description": f"Maximum value for {prop_name}{desc_suffix}",
                }
            else:
                props_dict[prop_slug] = {
                    "type": "string",
                    "description": f"Exact match for {description or prop_name}{desc_suffix}",
                }
                props_dict[f"{prop_slug}_contains"] = {
                    "type": "string",
                    "description": f"Substring match for {prop_name}{desc_suffix}",
                }

        return {
            "type": "object",
            "properties": props_dict,
            "additionalProperties": False,
        }

    @staticmethod
    def _build_aggregate_params(
        properties: list[dict[str, Any]], obj_name: str
    ) -> dict[str, Any]:
        """Build flat parameter schema for aggregate tool."""
        props_dict: dict[str, Any] = {}
        group_enum: list[str] = []
        metric_enum: list[str] = ["count"]

        for prop in properties:
            prop_name = prop.get("name", "")
            prop_slug = prop.get("slug", "")
            prop_type = prop.get("type", "string")
            description = prop.get("description", "")

            if not prop_slug:
                continue

            group_enum.append(prop_slug)
            desc_suffix = f" ({prop_name})" if prop_name else ""
            if prop_type in ("integer", "float", "number"):
                props_dict[prop_slug] = {
                    "type": "number",
                    "description": f"Exact match for {description or prop_name}{desc_suffix}",
                }
                props_dict[f"{prop_slug}_min"] = {
                    "type": "number",
                    "description": f"Minimum value for {prop_name}{desc_suffix}",
                }
                props_dict[f"{prop_slug}_max"] = {
                    "type": "number",
                    "description": f"Maximum value for {prop_name}{desc_suffix}",
                }
                metric_enum.extend([
                    f"{prop_slug}_sum",
                    f"{prop_slug}_avg",
                    f"{prop_slug}_min",
                    f"{prop_slug}_max",
                ])
            else:
                props_dict[prop_slug] = {
                    "type": "string",
                    "description": f"Exact match for {description or prop_name}{desc_suffix}",
                }
                props_dict[f"{prop_slug}_contains"] = {
                    "type": "string",
                    "description": f"Substring match for {prop_name}{desc_suffix}",
                }

        props_dict["group_by"] = {
            "type": "string",
            "enum": group_enum,
            "description": "Property slug to group by",
        }
        props_dict["metric"] = {
            "type": "string",
            "enum": metric_enum,
            "description": "Aggregation metric: count or <slug>_sum/_avg/_min/_max",
        }
        props_dict["limit"] = {
            "type": "integer",
            "description": "Maximum number of groups to return",
        }

        return {
            "type": "object",
            "properties": props_dict,
            "required": ["group_by", "metric"],
            "additionalProperties": False,
        }

