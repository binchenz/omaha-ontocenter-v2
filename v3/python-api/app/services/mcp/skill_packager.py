"""Generate installable Skill packages for downstream agents."""

import json


def generate_skill(ontology_name: str, ontology_slug: str, mcp_endpoint: str, tools: list[dict]) -> dict:
    """Generate a skill package following skill-creator format."""
    return {
        "skill_name": f"fin-{ontology_slug}",
        "version": "1.0.0",
        "description": f"{ontology_name} 数据查询能力 — 由 OntoCenter 自动生成",
        "mcp_config": {
            "mcpServers": {
                f"ontocenter-{ontology_slug}": {
                    "url": mcp_endpoint,
                    "transport": "http",
                }
            }
        },
        "tools": [t["name"] for t in tools],
        "examples": [
            f"查询{ontology_name}的前10条数据",
            f"按分类统计{ontology_name}数量",
            f"从{ontology_name}导航到关联对象",
        ],
    }


def generate_skill_markdown(skill_data: dict) -> str:
    """Generate SKILL.md content."""
    return f"""# {skill_data['skill_name']}

{skill_data['description']}

## 安装方式

将此 Skill 复制到你的 Agent 配置目录，Agent 将获得以下能力：

## 可用工具

{chr(10).join(f'- {t}' for t in skill_data['tools'])}

## 使用示例

{chr(10).join(f'- {ex}' for ex in skill_data['examples'])}

## MCP 配置

```json
{json.dumps(skill_data['mcp_config'], indent=2, ensure_ascii=False)}
```
"""


def generate_mcp_config(ontology_slug: str, endpoint: str) -> dict:
    return {
        "mcpServers": {
            f"ontocenter-{ontology_slug}": {
                "url": endpoint,
                "transport": "http",
            }
        }
    }
