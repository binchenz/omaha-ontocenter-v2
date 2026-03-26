# Setup Guide

## Step 1: Get Invite

Contact the administrator for access to https://ontocenter.example.com

## Step 2: Register Account

Create an account at the provided URL.

## Step 3: Get API Key

Navigate to Settings → API Keys and generate a new key.

## Step 4: Set Environment Variable

```bash
export ONTOCENTER_API_KEY="your-api-key-here"
```

Add to `~/.zshrc` or `~/.bashrc` for persistence.

## Test Connection

```bash
curl -H "X-API-Key: $ONTOCENTER_API_KEY" \
  https://ontocenter.example.com/api/v1/query/objects
```

Expected: JSON list of available objects.
