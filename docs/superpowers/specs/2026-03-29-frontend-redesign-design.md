# Frontend Redesign Design Spec
Date: 2026-03-29

## Overview

Upgrade the Omaha OntoCenter frontend from Ant Design to shadcn/ui + Tailwind CSS, add 4 new features (Watchlist page, Query History tab, Aggregate Query tab, Chat Session Management tab), and restructure navigation from a top header to a left sidebar.

## Tech Stack Change

**From:** React 18 + TypeScript + Vite + Ant Design
**To:** React 18 + TypeScript + Vite + shadcn/ui + Tailwind CSS

Ant Design is removed entirely. All existing components are rewritten using shadcn/ui primitives and Tailwind utility classes.

## Design System

- **Style:** Dark Mode OLED (`#0a0a0a` background, `#111111` surface)
- **Primary color:** `#2563EB` (blue-600)
- **Typography:** Fira Code (monospace/data), Fira Sans (UI text)
- **Pattern:** Real-Time / Operations Dashboard

## Navigation Architecture

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Sidebar (240px, fixed)  │  Main Content Area         │
│                         │                            │
│  Omaha OntoCenter       │  <page content>            │
│  ─────────────────      │                            │
│  📁 Projects            │                            │
│  ⭐ Watchlist           │                            │
│  ─────────────────      │                            │
│  👤 username            │                            │
│     Logout              │                            │
└─────────────────────────────────────────────────────┘
```

- Sidebar is persistent on desktop (≥1024px), collapsible on mobile
- Active nav item highlighted with blue-600 left border + background tint
- User menu at bottom of sidebar

### Routes

```
/projects                    → ProjectList
/projects/:id                → ProjectDetail (5 tabs)
/watchlist                   → Watchlist (new)
/login                       → Login
/register                    → Register
```

## ProjectDetail — 5 Tabs

Existing 6 tabs restructured to 5:

| Tab | Content | Status |
|-----|---------|--------|
| Config | YAML editor (CodeMirror) | existing |
| Ontology | Ontology viewer | existing |
| Explorer | Object explorer + **Query sub-tabs** | existing + new |
| Assets | Asset list | existing |
| Chat | Chat agent + **session list sidebar** | existing + new |

API Keys tab moves to user settings (future) or stays as a button in Config tab header.

### Explorer Tab — Query Sub-tabs

The Explorer tab gains a secondary tab bar:

```
[ Objects ] [ Query ] [ Aggregate ] [ History ]
```

- **Objects:** existing ObjectExplorer component
- **Query:** standard query builder (filter by object type, fields, operators)
- **Aggregate:** aggregate query builder (select object, field, function: avg/max/min/sum/count)
- **History:** paginated list of past queries with timestamp, object type, filters, result count; click to re-run

### Chat Tab — Session Management

Left panel (200px) lists chat sessions. Right panel shows active session messages.

```
┌──────────────┬────────────────────────────────┐
│ Sessions     │  Chat messages                  │
│ ──────────── │                                 │
│ + New        │  [message thread]               │
│              │                                 │
│ Session 1    │                                 │
│ Session 2    │  [input box]                    │
└──────────────┴────────────────────────────────┘
```

## Watchlist Page

Standalone page at `/watchlist`. Uses the public API (`/api/public/v1/watchlist`) with the user's API token.

```
┌─────────────────────────────────────────────────┐
│ Watchlist                          [+ Add Stock] │
│                                                  │
│ Code      Name    Note          Added    Action  │
│ 000001.SZ 平安银行  等待回调      2026-03-29  🗑   │
│ 600519.SH 贵州茅台  长期持有      2026-03-28  🗑   │
└─────────────────────────────────────────────────┘
```

- Add dialog: input ts_code + optional note
- Delete with confirmation
- Requires user to have an API key configured (shows prompt if none)

## Component Architecture

```
src/
├── components/
│   ├── Layout/
│   │   ├── Sidebar.tsx          ← new (replaces MainLayout header)
│   │   └── MainLayout.tsx       ← updated (sidebar + outlet)
│   ├── ui/                      ← shadcn/ui primitives (button, card, tabs, dialog, etc.)
│   └── ApiKeyManager.tsx        ← existing, restyled
├── pages/
│   ├── ProjectList.tsx          ← restyled
│   ├── ProjectDetail.tsx        ← restructured tabs
│   ├── ObjectExplorer.tsx       ← restyled, moved into Explorer tab
│   ├── QueryBuilder.tsx         ← new
│   ├── AggregateQuery.tsx       ← new
│   ├── QueryHistory.tsx         ← new
│   ├── Watchlist.tsx            ← new
│   ├── ChatAgent.tsx            ← restyled + session sidebar
│   ├── Login.tsx                ← restyled
│   └── Register.tsx             ← restyled
└── services/
    ├── watchlist.ts             ← new (wraps public watchlist API)
    └── queryHistory.ts          ← new (local storage or backend)
```

## Query History Storage

Query history is stored in **localStorage** (no backend changes needed). Each entry:
```ts
{ id, timestamp, projectId, objectType, filters, resultCount }
```
Max 100 entries, oldest dropped when limit reached.

## API Integration

- Watchlist: `GET/POST/DELETE /api/public/v1/watchlist` — requires API token from user's API keys
- Aggregate: `POST /api/public/v1/aggregate` — existing endpoint
- Query History: localStorage only

## Migration Strategy

1. Install Tailwind CSS + shadcn/ui alongside existing Ant Design
2. Build new Sidebar + MainLayout first (layout shell)
3. Migrate pages one by one, starting with Login/Register (simplest)
4. Migrate ProjectList, then ProjectDetail
5. Add new pages: Watchlist, QueryBuilder, AggregateQuery, QueryHistory
6. Remove Ant Design dependency last

## Out of Scope

- Backend changes (none required)
- Mobile app
- Dark/light mode toggle (dark only for now)
- Real-time data refresh
