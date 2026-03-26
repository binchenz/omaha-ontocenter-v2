# Financial Ontology Skill

Query financial data using Omaha OntoCenter's ontology system.

## Quick Start

1. **Configure MCP** - See [mcp-setup.md](mcp-setup.md)
2. **Read the skill** - See [SKILL.md](SKILL.md)
3. **Try examples** - See [examples.md](examples.md)

## What This Skill Does

Enables Claude Code to query financial data through natural language:
- Stock information and screening
- Financial indicators (P/E, ROE, margins, etc.)
- Balance sheets and cash flows
- Multi-object joins and comparisons
- Save and reuse queries as assets

## Files

- `SKILL.md` - Main skill documentation
- `examples.md` - Query examples and patterns
- `mcp-setup.md` - MCP configuration guide
- `README.md` - This file

## Usage

Once configured, simply ask Claude Code:
- "查找所有银行股"
- "平安银行的市盈率和ROE"
- "对比几只股票的财务指标"

Claude will use the MCP tools to query the ontology system.

## Sharing

To share with others:
1. Copy this entire directory to their `.claude/skills/`
2. They configure their own MCP connection (see mcp-setup.md)
3. Generate API keys for each user

## Support

For issues or questions, refer to the main project documentation.
