"""Generate MCP tool definitions from ontology objects."""


def generate_tools(ontology_id: str, objects: list[dict], links: list[dict], functions: list[dict]) -> list[dict]:
    """Generate MCP tool definitions for each ontology object."""
    tools = []

    for obj in objects:
        slug = obj["slug"]
        obj_name = obj.get("name", slug)
        desc = obj.get("description", "")

        tools.append({
            "name": f"search_{slug}",
            "description": f"搜索{obj_name}。{desc}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filters": {"type": "object", "description": "过滤条件, key为字段名, value为搜索值"},
                    "limit": {"type": "integer", "default": 50, "description": "返回数量上限"},
                },
            },
        })

        tools.append({
            "name": f"count_{slug}",
            "description": f"统计{obj_name}数量",
            "inputSchema": {"type": "object", "properties": {"filters": {"type": "object"}}},
        })

        tools.append({
            "name": f"aggregate_{slug}",
            "description": f"按维度聚合查询{obj_name}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "measures": {"type": "array", "items": {"type": "string"}, "description": "聚合指标, 如 ['SUM(amount)', 'AVG(price)']"},
                    "group_by": {"type": "array", "items": {"type": "string"}, "description": "分组字段"},
                },
            },
        })

    if len(objects) > 1:
        tools.append({
            "name": "navigate_path",
            "description": "跨对象路径导航，从起始对象通过链接关系导航到目标对象",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start_object": {"type": "string", "description": "起始对象"},
                    "start_id": {"type": "string", "description": "起始对象的主键值"},
                    "path": {"type": "array", "items": {"type": "string"}, "description": "导航路径, 如 ['Customer', 'Order']"},
                },
            },
        })

    if functions:
        tools.append({
            "name": "call_function",
            "description": "调用本体注册的计算函数",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "function_name": {"type": "string", "description": "函数名"},
                    "kwargs": {"type": "object", "description": "函数参数"},
                },
            },
        })

    return tools
