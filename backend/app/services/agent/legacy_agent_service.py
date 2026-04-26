from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.services.ontology_store import OntologyStore
from app.services.agent.legacy_tools import get_tools, execute_tool


class AgentService:
    """Agent service that dispatches tool calls based on user queries."""

    def __init__(self, db: Session, tenant_id: int, config_yaml: str = None):
        self.db = db
        self.tenant_id = tenant_id
        self.config_yaml = config_yaml
        self.store = OntologyStore(db)

    def get_agent_context(self) -> str:
        """Build the agent system prompt with tenant ontology context."""
        ontology = self.store.get_full_ontology(self.tenant_id)
        lines = [
            "You are a data analyst assistant for a business intelligence platform.",
            "You have access to the following ontology objects and their properties:",
        ]
        for obj in ontology.get("objects", []):
            lines.append(f"\nObject: {obj['name']}")
            lines.append(f"  Source: {obj['source_entity']} ({obj['datasource_id']})")
            if obj.get("description"):
                lines.append(f"  Description: {obj['description']}")
            if obj.get("properties"):
                parts = []
                for p in obj["properties"]:
                    st = f"/{p['semantic_type']}" if p.get("semantic_type") else ""
                    parts.append(f"{p['name']}({p['type']}{st})")
                props = ", ".join(parts)
                lines.append(f"  Properties: {props}")
            if obj.get("health_rules"):
                lines.append(f"  Health Rules: {len(obj['health_rules'])} defined")
            if obj.get("goals"):
                lines.append(f"  Business Goals: {len(obj['goals'])} defined")

        if ontology.get("relationships"):
            lines.append("\nRelationships:")
            for rel in ontology["relationships"]:
                lines.append(f"  {rel['from']} -> {rel['to']} ({rel['type']})")

        lines.append(
            "\nAvailable tools: query_ontology_object, aggregate_ontology_object, "
            "get_ontology_schema, get_object_health_status"
        )
        lines.append(
            "Instructions: Use the tools to answer user questions. "
            "For multi-step questions, chain tool calls as needed."
        )
        return "\n".join(lines)

    def run(self, user_message: str) -> Dict[str, Any]:
        """Run the agent on a user message and return tool calls or direct response."""
        message_lower = user_message.lower()

        # Simple keyword-based intent routing
        if any(kw in message_lower for kw in ["schema", "结构", "columns", "字段"]):
            object_names = self._extract_object_names(user_message)
            if object_names:
                tool_results = []
                for name in object_names:
                    result = execute_tool(
                        "get_ontology_schema",
                        {"object_name": name},
                        self.db,
                        self.tenant_id,
                        self.config_yaml,
                    )
                    tool_results.append({"tool": "get_ontology_schema", "result": result})
                return {
                    "response": f"Schema information for {', '.join(object_names)} retrieved.",
                    "tool_calls": tool_results,
                }

        if any(kw in message_lower for kw in ["health", "健康", "status", "状态"]):
            object_names = self._extract_object_names(user_message)
            if object_names:
                tool_results = []
                for name in object_names:
                    result = execute_tool(
                        "get_object_health_status",
                        {"object_name": name},
                        self.db,
                        self.tenant_id,
                        self.config_yaml,
                    )
                    tool_results.append({"tool": "get_object_health_status", "result": result})
                return {
                    "response": f"Health status for {', '.join(object_names)} retrieved.",
                    "tool_calls": tool_results,
                }

        if any(kw in message_lower for kw in ["sum", "total", "count", "average", "avg", "聚合", "统计"]):
            object_names = self._extract_object_names(user_message)
            if object_names:
                tool_results = []
                for name in object_names:
                    result = execute_tool(
                        "aggregate_ontology_object",
                        {"object_name": name, "property": "total_amount", "aggregation": "SUM"},
                        self.db,
                        self.tenant_id,
                        self.config_yaml,
                    )
                    tool_results.append({"tool": "aggregate_ontology_object", "result": result})
                return {
                    "response": f"Aggregation results for {', '.join(object_names)} computed.",
                    "tool_calls": tool_results,
                }

        # Default: query object
        object_names = self._extract_object_names(user_message)
        if object_names:
            tool_results = []
            for name in object_names:
                result = execute_tool(
                    "query_ontology_object",
                    {"object_name": name},
                    self.db,
                    self.tenant_id,
                    self.config_yaml,
                )
                tool_results.append({"tool": "query_ontology_object", "result": result})
            return {
                "response": f"Query results for {', '.join(object_names)} retrieved.",
                "tool_calls": tool_results,
            }

        return {
            "response": "I'm not sure which object you're asking about. Could you specify an ontology object name?",
            "tool_calls": [],
        }

    def _extract_object_names(self, message: str) -> List[str]:
        """Extract ontology object names mentioned in the message."""
        objects = self.store.list_objects(self.tenant_id)
        names = []
        for obj in objects:
            if obj.name.lower() in message.lower():
                names.append(obj.name)
        return names
