# 项目结构重组 — 全面按领域分组

## 1. 目标

把扁平的 25+ 文件 services/、21 个 api/ 路由、混杂的 components/、根目录污染等问题一次性整理清楚，让代码库能承接 Phase 4+ 的代码量增长。

主线原则：**按"领域能力"分组，不按"开发阶段"或"技术层"分组**。

## 2. 范围

**包含：**
- `backend/app/services/` 按领域分子目录（ontology / data / agent / semantic / platform / legacy/financial）
- 文件同时重命名去除冲突前缀（`ontology_store.py` → `ontology/store.py`）
- `backend/app/api/` 按领域分子目录
- `backend/app/models/` + `backend/app/schemas/` 同样按领域分组
- `backend/tests/` 镜像 services/ 子目录
- 前端 `pages/`、`components/` 按领域分组，老页面 `legacy/`
- `configs/` 按通用 vs 金融分组
- `docs/` 按 api / guides / design / market_analysis / superpowers 分组
- 根目录污染清理
- 删除 `cache_service.py`（死代码）和 `agents/` 目录（重复实现）

**不包含（YAGNI）：**
- 不引入 DDD 严格分层
- 不引入新框架 / 工具链
- 不拆 `chat.py`（1083 行整体迁移，下一轮再拆）
- 不修改任何业务逻辑

## 3. 目标目录结构

### 3.1 `backend/app/services/`

```
services/
├─ ontology/
│   ├─ store.py              (was ontology_store.py)
│   ├─ importer.py           (was ontology_importer.py)
│   ├─ inferrer.py           (was ontology_inferrer.py)
│   ├─ draft_store.py        (was ontology_draft_store.py)
│   ├─ template_loader.py
│   └─ schema_scanner.py
├─ data/
│   ├─ cleaner.py            (was data_cleaner.py)
│   └─ uploaded_table_store.py
├─ agent/
│   ├─ react.py              (was services/agent.py)
│   ├─ toolkit.py            (was agent_tools.py)
│   ├─ chat_service.py       (was chat.py — 整体迁移不拆)
│   └─ chart_engine.py
├─ semantic/
│   ├─ service.py            (was semantic.py)
│   ├─ validator.py          (was semantic_validator.py)
│   ├─ formatter.py          (was semantic_formatter.py)
│   └─ computed_property.py  (was computed_property_engine.py)
├─ platform/
│   ├─ scheduler.py
│   ├─ pipeline_runner.py
│   ├─ audit.py
│   └─ datahub.py
└─ legacy/financial/
    ├─ omaha.py
    ├─ query_builder.py
    └─ ontology_cache_service.py
```

**删除：** `services/cache_service.py`（无人调用），`backend/app/agents/`（与 services/agent/ 重复）。

### 3.2 `backend/app/api/`

```
api/
├─ auth/
│   ├─ login.py              (was auth.py)
│   ├─ api_keys.py
│   └─ public_auth.py
├─ projects/
│   ├─ crud.py               (was projects.py)
│   ├─ members.py
│   ├─ assets.py
│   └─ audit.py
├─ chat/
│   ├─ chat.py
│   └─ agent.py
├─ ontology/
│   ├─ store.py              (was ontology_store_routes.py)
│   ├─ legacy.py             (was ontology.py)
│   └─ semantic.py
├─ pipelines/
│   └─ crud.py               (was pipelines.py)
├─ legacy/financial/
│   ├─ query.py
│   ├─ datasources.py
│   ├─ datahub.py
│   ├─ watchlist.py
│   └─ public_query.py
├─ deps.py                   (顶层共享)
└─ public_deps.py            (顶层共享)
```

`api/__init__.py` 的 router 注册要同步更新。

### 3.3 `backend/app/models/` + `schemas/`

```
models/
├─ auth/        (user, tenant, invite_code, api_key, public_api_key)
├─ project/     (project, project_member, audit_log)
├─ ontology/    (ontology, asset)
├─ chat/        (chat_session, query_history, public_query_log)
├─ pipeline/    (pipeline, pipeline_run)
└─ legacy/financial/  (cached_stock, cached_financial, cached_financial_statements, watchlist)

schemas/
├─ auth/        (auth, user, public_auth)
├─ project/     (project, asset)
├─ chat/        (chat, agent, structured_response)
├─ ontology/    (ontology, ontology_store, auto_model)
└─ legacy/financial/  (public_query, watchlist)
```

**关键约束：** SQLAlchemy `Base.metadata` 必须能找到所有 models，alembic autogenerate 才能工作。`models/__init__.py` re-export 所有模型类，保证现有 import 不破。

### 3.4 `backend/tests/`

```
tests/
├─ unit/
│   ├─ ontology/
│   ├─ data/
│   ├─ agent/
│   ├─ semantic/
│   └─ platform/
├─ api/
├─ integration/    (现有保留)
├─ fixtures/       (test_tushare_config.yaml 等)
└─ conftest.py
```

### 3.5 前端

```
frontend/src/
├─ pages/
│   ├─ assistant/
│   ├─ ontology/
│   ├─ dashboard/
│   ├─ apps/
│   ├─ settings/
│   └─ legacy/    (老 v1 pages: ObjectExplorer, OntologyEditor, OntologyMap, etc.)
├─ components/
│   ├─ chat/
│   ├─ ontology/  (was map/)
│   ├─ layout/    (was Layout/)
│   ├─ ui/        (shadcn primitives 不动)
│   └─ shared/    (PrivateRoute, RequireProject, ApiKeyManager, QueryChart)
├─ services/      (api 调用，不动)
├─ types/
├─ hooks/
├─ contexts/
└─ layouts/       (AppLayout, TopNav, ModuleSidebar 不动)
```

### 3.6 `configs/`

```
configs/
├─ templates/                (industry 模板，retail.yaml 等)
└─ legacy/financial/         (financial_stock_analysis.yaml, ppy_ontology.yaml)
```

`configs/templates/*.md`（positioning 文档）移到 `docs/design/`。

### 3.7 `docs/`

```
docs/
├─ api/                      (API_USAGE_GUIDE.md)
├─ guides/                   (omaha-intro.md, ONTOLOGY_DEMO.md, university-talk.md)
├─ design/                   (positioning + redesign docs)
├─ market_analysis/          (现有保留)
└─ superpowers/              (现有保留)
```

### 3.8 根目录清理

| 文件 | 处理 |
|------|------|
| `omaha.db` | `.gitignore` + 从 git 移除（不删本地） |
| `111.pem` | `.gitignore` + 从 git 移除（敏感） |
| `test_tushare_config.yaml` | 移到 `backend/tests/fixtures/` |
| 根目录 `__pycache__/` | `.gitignore` |

## 4. 迁移策略

### 4.1 Shim 兼容层

不直接改 import，先把代码挪到新位置，旧位置变 re-export shim：

```python
# backend/app/services/ontology_store.py  (旧位置，shim)
"""Deprecated path. Re-exports from app.services.ontology.store."""
from app.services.ontology.store import *  # noqa: F401,F403
from app.services.ontology.store import OntologyStore  # noqa: F401
```

旧 import 仍然工作 → 测试不会因路径变更挂掉 → 之后批量改 import → 删 shim。

### 4.2 用 `git mv` 保留历史

文件移动用 `git mv`，git 识别为 rename，blame 历史完整保留。

### 4.3 自动化 import 重写

写 `scripts/rewrite_imports.py`，按映射表批量改：

```python
mapping = {
    r"from app\.services\.ontology_store ": "from app.services.ontology.store ",
    r"from app\.services\.ontology_importer ": "from app.services.ontology.importer ",
    r"from app\.services\.ontology_inferrer ": "from app.services.ontology.inferrer ",
    r"from app\.services\.ontology_draft_store ": "from app.services.ontology.draft_store ",
    r"from app\.services\.template_loader ": "from app.services.ontology.template_loader ",
    r"from app\.services\.schema_scanner ": "from app.services.ontology.schema_scanner ",
    r"from app\.services\.data_cleaner ": "from app.services.data.cleaner ",
    r"from app\.services\.uploaded_table_store ": "from app.services.data.uploaded_table_store ",
    r"from app\.services\.agent ": "from app.services.agent.react ",
    r"from app\.services\.agent_tools ": "from app.services.agent.toolkit ",
    r"from app\.services\.chat ": "from app.services.agent.chat_service ",
    r"from app\.services\.chart_engine ": "from app.services.agent.chart_engine ",
    r"from app\.services\.semantic ": "from app.services.semantic.service ",
    r"from app\.services\.semantic_validator ": "from app.services.semantic.validator ",
    r"from app\.services\.semantic_formatter ": "from app.services.semantic.formatter ",
    r"from app\.services\.computed_property_engine ": "from app.services.semantic.computed_property ",
    r"from app\.services\.scheduler ": "from app.services.platform.scheduler ",
    r"from app\.services\.pipeline_runner ": "from app.services.platform.pipeline_runner ",
    r"from app\.services\.audit ": "from app.services.platform.audit ",
    r"from app\.services\.datahub ": "from app.services.platform.datahub ",
    r"from app\.services\.omaha ": "from app.services.legacy.financial.omaha ",
    r"from app\.services\.query_builder ": "from app.services.legacy.financial.query_builder ",
    r"from app\.services\.ontology_cache_service ": "from app.services.legacy.financial.ontology_cache_service ",
    # models / schemas / api / frontend 类似
}
```

跑完后人工 review 关键文件（`chat_service.py`、`react.py`、`api/__init__.py`）确认无误。

### 4.4 验证关卡

每个阶段独立 commit，commit 前必须：
- `pytest tests/` 全套（基线 436 passed / 9 pre-existing failed，零新增回归）
- `npm run build`（前端动了才跑）
- `python -m app.main` 能启动（catch import 错误）

任一项失败立刻回退当前阶段，不继续。

## 5. 分 10 个 phase 执行

| Phase | 内容 | 风险 |
|-------|------|------|
| 0 | 准备：worktree、基线测试、确认 `agents/` 无人使用、写 rewrite_imports 脚本 | 低 |
| 1 | 根目录清理（gitignore、移文件） | 低 |
| 2 | services/ 重组：叶子层先挪 → 中层 → 顶层 → 删 agents/ | 高 |
| 3 | services/ import 路径修正、删 shim | 中 |
| 4 | tests/ 镜像重组 + fixtures/ | 低 |
| 5 | models/ 分组（注意 alembic autogenerate） | 中 |
| 6 | schemas/ 分组 | 低 |
| 7 | api/ 重组 + router 注册更新 | 中 |
| 8 | configs/ + docs/ 整理 | 低 |
| 9 | 前端重组：pages/、components/、layouts/ 不动 | 中 |
| 10 | 全套验证 + 启动 E2E + 更新 CLAUDE.md + 合并 | 低 |

每个 phase 内部按"叶子优先"顺序挪文件。

## 6. agents/ 与 services/agent/ 命名冲突处理

现状：`backend/app/agents/agent_service.py` 和 `backend/app/services/agent.py` 是两套并存的 agent 实现。

依赖摸底已确认 `api/agent.py` 用 `services/agent.py`，**不**用 `agents/`。Phase 0 grep 二次确认后：
- `services/agent.py` → 移到 `services/agent/react.py`
- 整个 `backend/app/agents/` 目录删除

如果 Phase 0 grep 发现 `agents/` 有真实调用方（不太可能），降级处理：保留为 `services/agent/legacy_agent_service.py`，下个 phase 整合。

## 7. SQLAlchemy + Alembic 风险

models 分组的最大风险是 alembic autogenerate 找不到所有模型类。缓解：

- `backend/app/models/__init__.py` 显式 import 并 re-export 所有模型类
- 同样在每个子目录的 `__init__.py` re-export 子目录下的模型
- alembic 的 `target_metadata = Base.metadata` 不变
- Phase 5 完成后跑 `alembic check`（看是否检测到不必要的 schema 变更）；如果检测到不该有的变更，说明某些模型没被加载

## 8. 测试策略

每个 phase 后跑：

```bash
# 全套后端
cd backend && /Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/ -q --tb=line

# 启动检查
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m app.main
# 应能成功打印 "Application startup complete." 然后 ctrl+c

# 前端（仅前端动了）
cd frontend && npm run build
```

最终 phase 10 跑一次完整 E2E 流程（参考 `/tmp/e2e_3b.py`）：登录 → 创建项目 → 上传 → 评估 → 建模 → 确认。

## 9. 与未来工作的关系

重组完成后，下面这些事情成本会降低：

- `chat.py` 1083 行后续拆成 session_service / prompt_builder / tool_dispatcher（已经在 `agent/` 子目录里好操作）
- Phase 4a 加 anomaly_detector / health_rule_evaluator → 直接落到 `agent/` 或 `data/` 子目录
- Phase 5 加 SaaS 连接器（金蝶/用友）→ `connectors/` 已分组，新增 `connectors/kingdee.py`、`connectors/yonyou.py`
- 前端 v1 页面退役 → 直接删 `pages/legacy/`

## 10. 风险与缓解

- **大爆炸式重组容易出错**：用 shim + 分 10 phase + 每 phase 跑测试缓解
- **import 重写脚本误伤**：rewrite_imports.py 用精确正则，跑完人工 review 关键文件
- **alembic 检测出 schema drift**：Phase 5 后跑 alembic check 验证
- **前端动了某些文件让 v2 路由挂掉**：Phase 9 跑 npm build + 启 dev server 手动点一遍 `/app/*` 路由
- **work tree 期间 main 有新提交**：Phase 0 之前同步 main，过程中尽量不并行其他工作
