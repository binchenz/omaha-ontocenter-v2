"""Ontology-based cache service using OmahaService."""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.legacy.financial.omaha import OmahaService
from app.services.semantic.formatter import SemanticTypeFormatter


class OntologyCacheService:
    """Service for querying cached data through ontology configuration."""

    def __init__(self, db: Session, config_path: str = None):
        self.db = db
        self.omaha = OmahaService()
        if config_path is None:
            import os
            # Get project root directory — file lives in backend/app/services/legacy/financial/
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            config_path = os.path.join(repo_root, 'configs', 'legacy', 'financial', 'financial_stock_analysis.yaml')
        with open(config_path, 'r') as f:
            self.config_yaml = f.read()

    def query_objects(
        self,
        object_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        format_output: bool = False,
        order_by: Optional[str] = None,
        order: str = "desc",
        select: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Query objects through OmahaService with ontology support."""
        # Convert dict filters to list format for OmahaService
        filter_list = []
        if filters:
            for field, value in filters.items():
                filter_list.append({"field": field, "operator": "=", "value": value})

        # Query through OmahaService (applies default_filters automatically)
        result = self.omaha.query_objects(
            config_yaml=self.config_yaml,
            object_type=object_type,
            filters=filter_list,
            limit=limit + offset  # OmahaService doesn't support offset, fetch more
        )

        if not result.get("success"):
            return []

        data = result.get("data", [])

        # Apply offset manually
        data = data[offset:offset + limit]

        # Format output if requested
        if format_output:
            data = self._format_data(object_type, data)

        # Apply sorting if requested
        if order_by and data:
            reverse = (order.lower() == "desc")
            try:
                data = sorted(data, key=lambda x: (x.get(order_by) is None, x.get(order_by, 0)), reverse=reverse)
            except:
                pass

        # Apply field selection if requested
        if select and data:
            data = [{k: v for k, v in record.items() if k in select} for record in data]

        return data

    def _format_data(self, object_type: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format data based on semantic types from ontology."""
        # Get object definition
        import yaml
        config = yaml.safe_load(self.config_yaml)
        obj_def = next((o for o in config['ontology']['objects'] if o['name'] == object_type), None)
        if not obj_def:
            return data

        # Build semantic type map
        semantic_types = {}
        for prop in obj_def.get('properties', []):
            if 'semantic_type' in prop:
                semantic_types[prop['name']] = prop['semantic_type']

        # Format each record
        formatted = []
        for record in data:
            # 保存原始数值副本用于计算
            raw_record = {}
            for key, value in record.items():
                # 尝试转换为数值
                if isinstance(value, str) and value:
                    # 移除货币符号和单位，处理亿/万
                    clean_value = value.replace('¥', '').replace('%', '').strip()
                    if '亿' in clean_value:
                        clean_value = str(float(clean_value.replace('亿', '')) * 1e8)
                    elif '万' in clean_value:
                        clean_value = str(float(clean_value.replace('万', '')) * 1e4)
                    try:
                        raw_record[key] = float(clean_value)
                    except:
                        raw_record[key] = value
                else:
                    raw_record[key] = value

            formatted_record = {}
            for key, value in record.items():
                if key in semantic_types and value is not None:
                    formatted_record[key] = SemanticTypeFormatter.format_value(value, semantic_types[key])
                else:
                    formatted_record[key] = value

            # Add computed properties using raw values
            for comp_prop in obj_def.get('computed_properties', []):
                prop_name = comp_prop['name']
                expression = comp_prop['expression']
                semantic_type = comp_prop.get('semantic_type', 'number')

                computed_value = SemanticTypeFormatter.compute_property(expression, raw_record)
                if computed_value is not None:
                    formatted_record[prop_name] = SemanticTypeFormatter.format_value(computed_value, semantic_type)

            formatted.append(formatted_record)
        
        return formatted

    def get_object_schema(self, object_type: str) -> Dict[str, Any]:
        """Get object schema with business context."""
        import yaml
        config = yaml.safe_load(self.config_yaml)
        obj_def = next((o for o in config['ontology']['objects'] if o['name'] == object_type), None)
        if not obj_def:
            return {}

        return {
            "object_type": object_type,
            "description": obj_def.get('description', ''),
            "business_context": obj_def.get('business_context', ''),
            "fields": [
                {
                    "name": p['name'],
                    "type": p['type'],
                    "semantic_type": p.get('semantic_type'),
                    "description": p.get('description', '')
                }
                for p in obj_def.get('properties', [])
            ],
            "computed_properties": [
                {
                    "name": cp['name'],
                    "expression": cp['expression'],
                    "semantic_type": cp.get('semantic_type'),
                    "description": cp.get('description', '')
                }
                for cp in obj_def.get('computed_properties', [])
            ]
        }

    def aggregate_objects(
        self,
        object_type: str,
        filters: Optional[Dict[str, Any]] = None,
        aggregations: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Aggregate data with functions like count, avg, max, min."""
        # Get raw data without formatting
        filter_list = []
        if filters:
            for field, value in filters.items():
                filter_list.append({"field": field, "operator": "=", "value": value})

        result = self.omaha.query_objects(
            config_yaml=self.config_yaml,
            object_type=object_type,
            filters=filter_list,
            limit=10000
        )

        data = result.get("data", [])

        results = {}
        for agg in aggregations:
            field = agg.get("field")
            func = agg.get("function", "count").lower()

            if func == "count":
                results[f"{field}_{func}"] = len([d for d in data if d.get(field) is not None])
            else:
                values = [d.get(field) for d in data if d.get(field) is not None and isinstance(d.get(field), (int, float))]
                if values:
                    if func == "avg":
                        results[f"{field}_{func}"] = round(sum(values) / len(values), 2)
                    elif func == "max":
                        results[f"{field}_{func}"] = max(values)
                    elif func == "min":
                        results[f"{field}_{func}"] = min(values)
                    elif func == "sum":
                        results[f"{field}_{func}"] = sum(values)

        return {"results": results, "count": len(data)}
