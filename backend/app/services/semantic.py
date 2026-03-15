"""Semantic layer service — parses extended YAML and expands computed fields to SQL."""
import re
import yaml
from typing import Any, Dict, List, Optional


class SemanticService:

    def parse_config(self, config_yaml: str) -> Dict[str, Any]:
        try:
            config = yaml.safe_load(config_yaml)
        except yaml.YAMLError as e:
            return {"valid": False, "error": str(e), "objects": {}, "metrics": []}

        if not isinstance(config, dict):
            return {"valid": False, "error": "Config must be a YAML dict", "objects": {}, "metrics": []}

        ontology = config.get("ontology", {})
        objects = {}

        for obj_def in ontology.get("objects", []):
            name = obj_def.get("name")
            if not name:
                continue

            base_props, computed_props, prop_map = {}, {}, {}

            for prop in obj_def.get("properties", []):
                prop_name = prop.get("name")
                if not prop_name:
                    continue
                if prop.get("semantic_type") == "computed":
                    computed_props[prop_name] = prop
                else:
                    col = prop.get("column", prop_name)
                    base_props[prop_name] = prop
                    prop_map[prop_name] = col

            objects[name] = {
                "description": obj_def.get("description"),
                "base_properties": base_props,
                "computed_properties": computed_props,
                "property_map": prop_map,
                "relationships": ontology.get("relationships", []),
            }

        return {"valid": True, "error": None, "objects": objects, "metrics": ontology.get("metrics", [])}

    def expand_formula(self, formula: str, property_map: Dict[str, str]) -> str:
        self._validate_no_unknown_props(formula, formula, property_map)
        expanded = self._expand_if(formula, property_map)
        result = expanded
        for prop_name, col_name in sorted(property_map.items(), key=lambda x: -len(x[0])):
            result = re.sub(r'\b' + re.escape(prop_name) + r'\b', col_name, result)
        return result

    def _expand_if(self, formula: str, property_map: Dict[str, str]) -> str:
        pattern = r'IF\s*\((.+),\s*(.+),\s*(.+)\)'
        match = re.search(pattern, formula, re.IGNORECASE)
        if not match:
            return formula
        condition = match.group(1).strip()
        true_val = match.group(2).strip()
        false_val = match.group(3).strip()
        for prop_name, col_name in sorted(property_map.items(), key=lambda x: -len(x[0])):
            condition = re.sub(r'\b' + re.escape(prop_name) + r'\b', col_name, condition)
        true_sql = "1" if true_val.lower() == "true" else ("0" if true_val.lower() == "false" else true_val)
        false_sql = "0" if false_val.lower() == "false" else ("1" if false_val.lower() == "true" else false_val)
        return formula[:match.start()] + f"CASE WHEN {condition} THEN {true_sql} ELSE {false_sql} END" + formula[match.end():]

    def _validate_no_unknown_props(self, expanded: str, original: str, property_map: Dict[str, str]) -> None:
        identifiers = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', original))
        sql_keywords = {
            'AND', 'OR', 'NOT', 'IF', 'TRUE', 'FALSE', 'NULL',
            'SUM', 'AVG', 'COUNT', 'MAX', 'MIN', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
            'true', 'false', 'null'
        }
        unknown = identifiers - set(property_map.keys()) - sql_keywords
        if unknown:
            raise ValueError(f"Formula references unknown property: {unknown}")

    def build_agent_context(self, obj_meta: Dict[str, Any]) -> str:
        lines = []
        if obj_meta.get("description"):
            lines.append(obj_meta["description"])
            lines.append("")
        lines.append("可用字段（查询时使用 ObjectName.field_name 格式）：")
        for name, prop in obj_meta["base_properties"].items():
            desc = prop.get("description", "")
            stype = prop.get("semantic_type", "")
            if stype == "currency":
                lines.append(f"  - {name} (货币, {prop.get('currency', '')}): {desc}")
            elif stype == "percentage":
                lines.append(f"  - {name} (百分比): {desc}")
            elif stype == "enum":
                vals = ", ".join(f"{e['value']}={e['label']}" for e in prop.get("enum_values", []))
                lines.append(f"  - {name} (枚举: {vals}): {desc}")
            else:
                lines.append(f"  - {name}: {desc}")
        for name, prop in obj_meta["computed_properties"].items():
            lines.append(f"  - {name} [计算字段，可直接查询]: {prop.get('description', '')}")
            if prop.get("business_context"):
                lines.append(f"    基准: {prop['business_context']}")
        return "\n".join(lines)

    def get_schema_with_semantics(self, config_yaml: str, object_type: str) -> Dict[str, Any]:
        result = self.parse_config(config_yaml)
        if not result["valid"]:
            return {"success": False, "error": result["error"]}
        obj = result["objects"].get(object_type)
        if not obj:
            return {"success": False, "error": f"Object '{object_type}' not found"}
        columns = []
        for name, prop in obj["base_properties"].items():
            col = {"name": name, "type": prop.get("type", "string"),
                   "semantic_type": prop.get("semantic_type"), "description": prop.get("description")}
            if prop.get("semantic_type") == "currency":
                col["currency"] = prop.get("currency")
            if prop.get("semantic_type") == "enum":
                col["enum_values"] = prop.get("enum_values", [])
            columns.append(col)
        for name, prop in obj["computed_properties"].items():
            columns.append({"name": name, "type": "computed", "formula": prop.get("formula"),
                            "return_type": prop.get("return_type"), "description": prop.get("description"),
                            "business_context": prop.get("business_context")})
        return {"success": True, "object_type": object_type, "description": obj.get("description"),
                "columns": columns,
                "relationships": [r for r in obj["relationships"]
                                  if r.get("from_object") == object_type or r.get("to_object") == object_type]}


semantic_service = SemanticService()
