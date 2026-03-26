# MCP Configuration Guide

## Quick Setup

### Step 1: Get Your API Key

1. Start the Omaha OntoCenter backend:
```bash
cd backend
uvicorn app.main:app --reload
```

2. Open http://localhost:8000/docs

3. Create a user account and login

4. Create a project with an ontology config

5. Generate an API key for the project (via API or web UI)

6. Copy the API key (format: `omaha_1_xxxxx`)

### Step 2: Configure MCP Server

Edit your MCP config file:
- **User-level:** `~/.claude/settings/mcp.json`
- **Workspace-level:** `.claude/settings/mcp.json`

Add this configuration:

```json
{
  "mcpServers": {
    "omaha-ontocenter": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/absolute/path/to/omaha_ontocenter/backend",
      "env": {
        "OMAHA_API_KEY": "omaha_1_your_key_here",
        "DATABASE_URL": "sqlite:///./omaha.db",
        "SECRET_KEY": "your-secret-key-here"
      }
    }
  }
}
```

**Important:**
- Use absolute path for `cwd`
- Replace `OMAHA_API_KEY` with your actual key
- Ensure Python environment has required packages installed

### Step 3: Verify Connection

Restart Claude Code, then test:

```
Use mcp__omaha-ontocenter__list_objects to verify connection
```

If successful, you'll see available business objects.

## Troubleshooting

### "MCP server not found"
- Check that `cwd` path is correct and absolute
- Verify Python is in PATH
- Ensure backend dependencies are installed

### "Invalid API key"
- Verify key format: `omaha_1_xxxxx`
- Check key is active in database
- Ensure key hasn't expired

### "No objects returned"
- Verify project has ontology config
- Check DATABASE_URL points to correct database
- Ensure project_id associated with API key has data

### "Module not found"
- Install backend dependencies: `pip install -r requirements.txt`
- Activate correct Python virtual environment
- Check `cwd` points to backend directory

## Advanced Configuration

### Using PostgreSQL

```json
{
  "env": {
    "OMAHA_API_KEY": "omaha_1_xxxxx",
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/omaha",
    "SECRET_KEY": "your-secret-key"
  }
}
```

### Multiple Projects

Create separate MCP server entries for different projects:

```json
{
  "mcpServers": {
    "omaha-project-a": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/path/to/backend",
      "env": {
        "OMAHA_API_KEY": "omaha_1_project_a_key"
      }
    },
    "omaha-project-b": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/path/to/backend",
      "env": {
        "OMAHA_API_KEY": "omaha_1_project_b_key"
      }
    }
  }
}
```

## Sharing with Others

To share this skill with others:

1. **Share the skill files:**
   - Copy `.claude/skills/financial-ontology/` directory
   - Others place it in their `.claude/skills/` directory

2. **Share MCP setup instructions:**
   - Provide this configuration guide
   - Share the backend repository access
   - Generate API keys for each user

3. **Share ontology configs:**
   - Export YAML configs from `configs/` directory
   - Users import via web UI or API

## Security Notes

- **Never commit API keys** to version control
- Use environment variables or secure vaults
- Rotate keys periodically
- Revoke unused keys
- Use project-specific keys for isolation
