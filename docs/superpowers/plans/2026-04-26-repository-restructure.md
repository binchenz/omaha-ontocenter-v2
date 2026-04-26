# 项目结构重组实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按领域能力分组重组 backend/services、api、models、schemas、tests 和 frontend，让代码库能承接 Phase 4+ 的代码量增长。

**Architecture:** 10 个 phase 渐进式迁移。每个 phase 用 `git mv` 保留 blame 历史，旧路径留 shim re-export 兼容层，`scripts/rewrite_imports.py` 批量改 import 后删 shim。每 phase 独立 commit + pytest 全套验证。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, React 18 + TypeScript + Vite

**Spec:** `docs/superpowers/specs/2026-04-26-repository-restructure-design.md`

**Python:** `/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python`

**Test baseline:** 436 passed / 9 pre-existing failed (zero new regression allowed)

---

### Task 0: Phase 0 — 准备工作

**Files:**
- Create: `scripts/rewrite_imports.py`
- Modify: `.gitignore`

- [ ] **Step 1: 创建 worktree + 分支**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git worktree add .worktrees/restructure -b feature/repository-restructure
cd .worktrees/restructure
```

- [ ] **Step 2: 复制 omaha.db 到 worktree**

```bash
cp /Users/wangfushuaiqi/omaha_ontocenter/omaha.db .
```

- [ ] **Step 3: 记录 pytest 基线**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
```

Expected: `436 passed, 9 failed` (或接近)。记录实际数字作为基线。

- [ ] **Step 4: 确认 agents/ 无人使用**

```bash
grep -r "from app\.agents" backend/app/ --include="*.py" -l
grep -r "from app import agents" backend/app/ --include="*.py" -l
grep -r "app\.agents" backend/app/ --include="*.py" -l
```

Expected: 无结果（或仅 agents/ 内部互引）。如果有外部调用方，记录并降级处理。

- [ ] **Step 5: 写 `scripts/rewrite_imports.py`**

```python
#!/usr/bin/env python3
"""Batch-rewrite import paths after services/ restructure."""
import re
import sys
from pathlib import Path

MAPPING = [
    # ontology domain
    (r"from app\.services\.ontology_store ", "from app.services.ontology.store "),
    (r"from app\.services\.ontology_importer ", "from app.services.ontology.importer "),
    (r"from app\.services\.ontology_inferrer ", "from app.services.ontology.inferrer "),
    (r"from app\.services\.ontology_draft_store ", "from app.services.ontology.draft_store "),
    (r"from app\.services\.template_loader ", "from app.services.ontology.template_loader "),
    (r"from app\.services\.schema_scanner ", "from app.services.ontology.schema_scanner "),
    # data domain
    (r"from app\.services\.data_cleaner ", "from app.services.data.cleaner "),
    (r"from app\.services\.uploaded_table_store ", "from app.services.data.uploaded_table_store "),
    # agent domain
    (r"from app\.services\.agent_tools\b", "from app.services.agent.toolkit"),
    (r"from app\.services\.agent\b(?!_|\.)", "from app.services.agent.react"),
    (r"from app\.services\.chat ", "from app.services.agent.chat_service "),
    (r"from app\.services\.chart_engine ", "from app.services.agent.chart_engine "),
    # semantic domain
    (r"from app\.services\.semantic ", "from app.services.semantic.service "),
    (r"from app\.services\.semantic_validator ", "from app.services.semantic.validator "),
    (r"from app\.services\.semantic_formatter ", "from app.services.semantic.formatter "),
    (r"from app\.services\.computed_property_engine ", "from app.services.semantic.computed_property "),
    # platform domain
    (r"from app\.services\.scheduler ", "from app.services.platform.scheduler "),
    (r"from app\.services\.pipeline_runner ", "from app.services.platform.pipeline_runner "),
    (r"from app\.services\.audit ", "from app.services.platform.audit "),
    (r"from app\.services\.datahub ", "from app.services.platform.datahub "),
    # legacy/financial domain
    (r"from app\.services\.omaha ", "from app.services.legacy.financial.omaha "),
    (r"from app\.services\.query_builder ", "from app.services.legacy.financial.query_builder "),
    (r"from app\.services\.ontology_cache_service ", "from app.services.legacy.financial.ontology_cache_service "),
]

def rewrite_file(path: Path, dry_run: bool = False) -> list[str]:
    text = path.read_text()
    changes = []
    for pattern, replacement in MAPPING:
        new_text = re.sub(pattern, replacement, text)
        if new_text != text:
            changes.append(f"  {pattern} -> {replacement}")
            text = new_text
    if changes and not dry_run:
        path.write_text(text)
    return changes

def main():
    dry_run = "--dry-run" in sys.argv
    root = Path("backend")
    files = list(root.rglob("*.py"))
    total = 0
    for f in sorted(files):
        changes = rewrite_file(f, dry_run=dry_run)
        if changes:
            print(f"{f}:")
            for c in changes:
                print(c)
            total += len(changes)
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Total rewrites: {total}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Commit Phase 0**

```bash
git add scripts/rewrite_imports.py
git commit -m "chore(phase0): add rewrite_imports script + record baseline"
```

---

### Task 1: Phase 1 — 根目录清理

**Files:**
- Modify: `.gitignore`
- Move: `test_tushare_config.yaml` → `backend/tests/fixtures/test_tushare_config.yaml`
- Remove from git: `111.pem`

- [ ] **Step 1: 更新 .gitignore**

在 `.gitignore` 末尾追加：

```
# Phase 1 cleanup
omaha.db
111.pem
__pycache__/
```

- [ ] **Step 2: git rm --cached 111.pem**

```bash
git rm --cached 111.pem
```

- [ ] **Step 3: 移动 test_tushare_config.yaml**

```bash
mkdir -p backend/tests/fixtures
git mv test_tushare_config.yaml backend/tests/fixtures/test_tushare_config.yaml
```

- [ ] **Step 4: 修复引用 test_tushare_config.yaml 的测试**

```bash
grep -r "test_tushare_config" backend/tests/ --include="*.py" -l
```

对找到的文件，把路径从 `test_tushare_config.yaml` 或 `../../test_tushare_config.yaml` 改为相对于 `backend/` 的 `tests/fixtures/test_tushare_config.yaml`。

- [ ] **Step 5: 验证**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
```

Expected: 与基线一致，零新增失败。

- [ ] **Step 6: Commit**

```bash
git add .gitignore backend/tests/fixtures/
git commit -m "chore(phase1): root cleanup — gitignore, remove 111.pem, move fixture"
```

---

### Task 2: Phase 2 — services/ 重组（git mv + shim）

**Files:**
- Move: 25 个 service 文件到 6 个子目录
- Create: 每个旧路径的 shim re-export 文件
- Create: 每个子目录的 `__init__.py`
- Delete: `backend/app/services/cache_service.py`, `backend/app/agents/` 目录

本 task 只做文件移动 + shim，不改任何 import。import 在 Task 3 统一处理。

- [ ] **Step 1: 创建子目录结构**

```bash
cd backend/app/services
mkdir -p ontology data agent semantic platform legacy/financial
touch ontology/__init__.py data/__init__.py agent/__init__.py semantic/__init__.py platform/__init__.py legacy/__init__.py legacy/financial/__init__.py
```

- [ ] **Step 2: git mv ontology 域文件**

```bash
cd backend/app/services
git mv ontology_store.py ontology/store.py
git mv ontology_importer.py ontology/importer.py
git mv ontology_inferrer.py ontology/inferrer.py
git mv ontology_draft_store.py ontology/draft_store.py
git mv template_loader.py ontology/template_loader.py
git mv schema_scanner.py ontology/schema_scanner.py
```

- [ ] **Step 3: 写 ontology 域 shim 文件**

为每个旧路径创建 shim。示例 `backend/app/services/ontology_store.py`：

```python
"""Deprecated path. Use app.services.ontology.store."""
from app.services.ontology.store import OntologyStore  # noqa: F401
```

同理为 `ontology_importer.py`、`ontology_inferrer.py`、`ontology_draft_store.py`、`template_loader.py`、`schema_scanner.py` 各写一个 shim，re-export 该文件的所有公开符号。

查找每个文件的公开符号：

```bash
grep "^class \|^def \|^[A-Z_]* =" backend/app/services/ontology/store.py
```

- [ ] **Step 4: git mv data 域文件**

```bash
git mv data_cleaner.py data/cleaner.py
git mv uploaded_table_store.py data/uploaded_table_store.py
```

写对应 shim（`data_cleaner.py`、`uploaded_table_store.py`）。

- [ ] **Step 5: git mv agent 域文件**

```bash
git mv agent.py agent/react.py
git mv agent_tools.py agent/toolkit.py
git mv chat.py agent/chat_service.py
git mv chart_engine.py agent/chart_engine.py
```

写对应 shim。注意 `agent.py` shim 需要 re-export `AgentService`（或实际类名），`chat.py` shim re-export `ChatService` 等。

- [ ] **Step 6: git mv semantic 域文件**

```bash
git mv semantic.py semantic/service.py
git mv semantic_validator.py semantic/validator.py
git mv semantic_formatter.py semantic/formatter.py
git mv computed_property_engine.py semantic/computed_property.py
```

写对应 shim。

- [ ] **Step 7: git mv platform 域文件**

```bash
git mv scheduler.py platform/scheduler.py
git mv pipeline_runner.py platform/pipeline_runner.py
git mv audit.py platform/audit.py
git mv datahub.py platform/datahub.py
```

写对应 shim。

- [ ] **Step 8: git mv legacy/financial 域文件**

```bash
git mv omaha.py legacy/financial/omaha.py
git mv query_builder.py legacy/financial/query_builder.py
git mv ontology_cache_service.py legacy/financial/ontology_cache_service.py
```

写对应 shim。

- [ ] **Step 9: 删除死代码**

```bash
git rm backend/app/services/cache_service.py
rm -rf backend/app/agents/
git add -u backend/app/agents/
```

- [ ] **Step 10: 验证 — shim 让所有旧 import 仍然工作**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -c "from app.services.ontology_store import OntologyStore; print('OK')"
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -c "from app.services.chat import ChatService; print('OK')"
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
```

Expected: 与基线一致。

- [ ] **Step 11: Commit**

```bash
git add backend/app/services/
git commit -m "refactor(phase2): reorganize services/ by domain with shim compat layer"
```

---

### Task 3: Phase 3 — services/ import 路径修正 + 删 shim

**Files:**
- Modify: 所有引用旧 services 路径的 `.py` 文件
- Delete: Phase 2 创建的所有 shim 文件

- [ ] **Step 1: dry-run rewrite_imports.py**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python scripts/rewrite_imports.py --dry-run
```

Review 输出，确认每条替换合理。

- [ ] **Step 2: 执行 rewrite**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python scripts/rewrite_imports.py
```

- [ ] **Step 3: 手动 review 关键文件**

检查以下文件的 import 是否正确：

```bash
head -30 backend/app/services/agent/chat_service.py
head -30 backend/app/services/agent/react.py
head -30 backend/app/api/__init__.py
head -20 backend/app/services/agent/toolkit.py
```

特别注意：
- `chat_service.py` 内部引用其他 services 的路径是否都被正确替换
- `react.py`（原 agent.py）引用 `agent_tools` 是否变成 `agent.toolkit`
- `api/__init__.py` 的 import 暂时不改（Phase 7 处理）

- [ ] **Step 4: 处理 rewrite_imports.py 未覆盖的 import 模式**

脚本只处理 `from app.services.X` 模式。检查是否有 `import app.services.X` 或 `from app.services import X` 模式：

```bash
grep -rn "import app\.services\." backend/ --include="*.py" | grep -v __pycache__ | grep -v "from app"
grep -rn "from app\.services import " backend/ --include="*.py" | grep -v __pycache__
```

手动修复找到的任何遗漏。

- [ ] **Step 5: 删除所有 shim 文件**

删除 Phase 2 在 `backend/app/services/` 根目录留下的 shim 文件（不是子目录里的文件）：

```bash
# 列出 services/ 根目录下的 .py 文件（排除 __init__.py）
ls backend/app/services/*.py | grep -v __init__
```

这些应该全是 shim。确认后删除：

```bash
git rm backend/app/services/ontology_store.py
git rm backend/app/services/ontology_importer.py
git rm backend/app/services/ontology_inferrer.py
git rm backend/app/services/ontology_draft_store.py
git rm backend/app/services/template_loader.py
git rm backend/app/services/schema_scanner.py
git rm backend/app/services/data_cleaner.py
git rm backend/app/services/uploaded_table_store.py
git rm backend/app/services/agent.py
git rm backend/app/services/agent_tools.py
git rm backend/app/services/chat.py
git rm backend/app/services/chart_engine.py
git rm backend/app/services/semantic.py
git rm backend/app/services/semantic_validator.py
git rm backend/app/services/semantic_formatter.py
git rm backend/app/services/computed_property_engine.py
git rm backend/app/services/scheduler.py
git rm backend/app/services/pipeline_runner.py
git rm backend/app/services/audit.py
git rm backend/app/services/datahub.py
git rm backend/app/services/omaha.py
git rm backend/app/services/query_builder.py
git rm backend/app/services/ontology_cache_service.py
```

- [ ] **Step 6: 验证**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -c "from app.services.ontology.store import OntologyStore; print('OK')"
```

Expected: 与基线一致。

- [ ] **Step 7: Commit**

```bash
git add -u
git commit -m "refactor(phase3): rewrite all service imports to new paths, remove shims"
```

---

### Task 4: Phase 4 — tests/ 镜像重组

**Files:**
- Move: `backend/tests/test_*.py` 到 `unit/{ontology,data,agent,semantic,platform}/` 子目录
- Keep: `backend/tests/conftest.py`, `backend/tests/integration/` 不动

- [ ] **Step 1: 创建 tests 子目录**

```bash
cd backend/tests
mkdir -p unit/ontology unit/data unit/agent unit/semantic unit/platform api
touch unit/__init__.py unit/ontology/__init__.py unit/data/__init__.py unit/agent/__init__.py unit/semantic/__init__.py unit/platform/__init__.py api/__init__.py
```

- [ ] **Step 2: 按领域移动测试文件**

ontology 域：
```bash
cd backend
git mv tests/test_ontology_store.py tests/unit/ontology/
git mv tests/test_ontology_importer.py tests/unit/ontology/
git mv tests/test_ontology_inferrer.py tests/unit/ontology/
git mv tests/test_ontology_inferrer_template.py tests/unit/ontology/
git mv tests/test_ontology_draft_store.py tests/unit/ontology/
git mv tests/test_template_loader.py tests/unit/ontology/
git mv tests/test_schema_scanner.py tests/unit/ontology/
git mv tests/test_ontology_redesign.py tests/unit/ontology/
git mv tests/test_ontology_api.py tests/unit/ontology/
git mv tests/test_granularity_save.py tests/unit/ontology/
```

data 域：
```bash
git mv tests/test_data_cleaner.py tests/unit/data/
git mv tests/test_uploaded_table_store.py tests/unit/data/
git mv tests/test_upload_tool.py tests/unit/data/
git mv tests/test_csv_quick_query.py tests/unit/data/
```

agent 域：
```bash
git mv tests/test_agent.py tests/unit/agent/
git mv tests/test_agent_service.py tests/unit/agent/
git mv tests/test_agent_tools.py tests/unit/agent/
git mv tests/test_agent_chart.py tests/unit/agent/
git mv tests/test_agent_llm.py tests/unit/agent/
git mv tests/test_agent_setup_stage.py tests/unit/agent/
git mv tests/test_chat_service.py tests/unit/agent/
git mv tests/test_chat_scenarios.py tests/unit/agent/
git mv tests/test_chat_refactor.py tests/unit/agent/
git mv tests/test_chat_upload.py tests/unit/agent/
git mv tests/test_chart_engine.py tests/unit/agent/
git mv tests/test_extract_structured.py tests/unit/agent/
git mv tests/test_phase3b_tools.py tests/unit/agent/
git mv tests/test_structured_response.py tests/unit/agent/
```

semantic 域：
```bash
git mv tests/test_semantic_service.py tests/unit/semantic/
git mv tests/test_semantic_validator.py tests/unit/semantic/
git mv tests/test_semantic_formatter.py tests/unit/semantic/
git mv tests/test_semantic_general.py tests/unit/semantic/
git mv tests/test_computed_properties.py tests/unit/semantic/
git mv tests/test_computed_property_engine.py tests/unit/semantic/
```

platform 域：
```bash
git mv tests/test_scheduler.py tests/unit/platform/
```

api 测试：
```bash
git mv tests/test_api_agent.py tests/api/
git mv tests/test_api_audit.py tests/api/
git mv tests/test_api_auto_model.py tests/api/
git mv tests/test_api_chat.py tests/api/
git mv tests/test_api_datasources.py tests/api/
git mv tests/test_api_members.py tests/api/
git mv tests/test_api_ontology_generate.py tests/api/
git mv tests/test_api_ontology_store.py tests/api/
git mv tests/test_api_pipelines.py tests/api/
git mv tests/test_api_public_auth.py tests/api/
git mv tests/test_api_semantic.py tests/api/
```

剩余文件（models/schemas/connector/integration 等）留在 `tests/` 根目录不动。

- [ ] **Step 3: 验证**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
```

Expected: 与基线一致。pytest 会自动递归发现子目录中的测试。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/
git commit -m "refactor(phase4): reorganize tests/ to mirror services/ domain structure"
```

---

### Task 5: Phase 5 — models/ 分组

**Files:**
- Move: `backend/app/models/*.py` 到子目录
- Modify: `backend/app/models/__init__.py` (re-export 所有模型类)
- Create: 每个子目录的 `__init__.py`

**关键约束：** `models/__init__.py` 必须 re-export 所有模型类，保证 `from app.models import User, Project, ...` 等现有 import 全部可用。`app/main.py`、`app/database.py` 不需修改。Alembic `Base.metadata` 必须能找到所有模型。

- [ ] **Step 1: 创建子目录**

```bash
cd backend/app/models
mkdir -p auth project ontology chat pipeline legacy/financial
```

- [ ] **Step 2: git mv auth 域模型**

```bash
cd backend/app/models
git mv user.py auth/user.py
git mv tenant.py auth/tenant.py
git mv invite_code.py auth/invite_code.py
git mv api_key.py auth/api_key.py
git mv public_api_key.py auth/public_api_key.py
```

创建 `auth/__init__.py`：

```python
from app.models.auth.user import User
from app.models.auth.tenant import Tenant
from app.models.auth.invite_code import InviteCode
from app.models.auth.api_key import ProjectApiKey
from app.models.auth.public_api_key import PublicApiKey
```

- [ ] **Step 3: git mv project 域模型**

```bash
git mv project.py project/project.py
git mv project_member.py project/project_member.py
git mv audit_log.py project/audit_log.py
```

创建 `project/__init__.py`：

```python
from app.models.project.project import Project
from app.models.project.project_member import ProjectMember
from app.models.project.audit_log import AuditLog
```

- [ ] **Step 4: git mv ontology 域模型**

```bash
git mv ontology.py ontology/ontology.py
git mv asset.py ontology/asset.py
```

创建 `ontology/__init__.py`：

```python
from app.models.ontology.ontology import (
    OntologyObject, ObjectProperty, OntologyRelationship,
    HealthRule, BusinessGoal, DomainKnowledge,
)
from app.models.ontology.asset import DatasetAsset, DataLineage
```

- [ ] **Step 5: git mv chat 域模型**

```bash
git mv chat_session.py chat/chat_session.py
git mv query_history.py chat/query_history.py
git mv public_query_log.py chat/public_query_log.py
```

创建 `chat/__init__.py`：

```python
from app.models.chat.chat_session import ChatSession, ChatMessage
from app.models.chat.query_history import QueryHistory
from app.models.chat.public_query_log import PublicQueryLog
```

- [ ] **Step 6: git mv pipeline 域模型**

```bash
git mv pipeline.py pipeline/pipeline.py
git mv pipeline_run.py pipeline/pipeline_run.py
```

创建 `pipeline/__init__.py`：

```python
from app.models.pipeline.pipeline import Pipeline
from app.models.pipeline.pipeline_run import PipelineRun
```

- [ ] **Step 7: git mv legacy/financial 域模型**

```bash
git mv cached_stock.py legacy/financial/cached_stock.py
git mv cached_financial.py legacy/financial/cached_financial.py
git mv cached_financial_statements.py legacy/financial/cached_financial_statements.py
git mv watchlist.py legacy/financial/watchlist.py
```

创建 `legacy/__init__.py` 和 `legacy/financial/__init__.py`：

```python
# legacy/financial/__init__.py
from app.models.legacy.financial.cached_stock import CachedStock
from app.models.legacy.financial.cached_financial import CachedFinancialIndicator
from app.models.legacy.financial.cached_financial_statements import CachedIncomeStatement, CachedBalanceSheet, CachedCashFlow
from app.models.legacy.financial.watchlist import Watchlist
```

- [ ] **Step 8: 重写 models/__init__.py**

```python
"""Models package — re-exports all model classes for backward compatibility."""
from app.models.auth import User, Tenant, InviteCode, ProjectApiKey, PublicApiKey
from app.models.project import Project, ProjectMember, AuditLog
from app.models.ontology import (
    OntologyObject, ObjectProperty, OntologyRelationship,
    HealthRule, BusinessGoal, DomainKnowledge,
    DatasetAsset, DataLineage,
)
from app.models.chat import ChatSession, ChatMessage, QueryHistory, PublicQueryLog
from app.models.pipeline import Pipeline, PipelineRun
from app.models.legacy.financial import CachedStock, CachedFinancialIndicator, CachedIncomeStatement, CachedBalanceSheet, CachedCashFlow, Watchlist

__all__ = [
    "User", "Tenant", "InviteCode", "ProjectApiKey", "PublicApiKey",
    "Project", "ProjectMember", "AuditLog",
    "OntologyObject", "ObjectProperty", "OntologyRelationship",
    "HealthRule", "BusinessGoal", "DomainKnowledge",
    "DatasetAsset", "DataLineage",
    "ChatSession", "ChatMessage", "QueryHistory", "PublicQueryLog",
    "Pipeline", "PipelineRun",
    "CachedStock", "CachedFinancialIndicator",
    "CachedIncomeStatement", "CachedBalanceSheet", "CachedCashFlow",
    "Watchlist",
]
```

- [ ] **Step 9: 用 rewrite_imports 脚本处理 models import（扩展脚本）**

在 `scripts/rewrite_imports.py` 的 MAPPING 中追加 models 映射：

```python
# models domain
(r"from app\.models\.user ", "from app.models.auth.user "),
(r"from app\.models\.tenant ", "from app.models.auth.tenant "),
(r"from app\.models\.invite_code ", "from app.models.auth.invite_code "),
(r"from app\.models\.api_key ", "from app.models.auth.api_key "),
(r"from app\.models\.public_api_key ", "from app.models.auth.public_api_key "),
(r"from app\.models\.project ", "from app.models.project.project "),
(r"from app\.models\.project_member ", "from app.models.project.project_member "),
(r"from app\.models\.audit_log ", "from app.models.project.audit_log "),
(r"from app\.models\.ontology ", "from app.models.ontology.ontology "),
(r"from app\.models\.asset ", "from app.models.ontology.asset "),
(r"from app\.models\.chat_session ", "from app.models.chat.chat_session "),
(r"from app\.models\.query_history ", "from app.models.chat.query_history "),
(r"from app\.models\.public_query_log ", "from app.models.chat.public_query_log "),
(r"from app\.models\.pipeline ", "from app.models.pipeline.pipeline "),
(r"from app\.models\.pipeline_run ", "from app.models.pipeline.pipeline_run "),
(r"from app\.models\.cached_stock ", "from app.models.legacy.financial.cached_stock "),
(r"from app\.models\.cached_financial_statements ", "from app.models.legacy.financial.cached_financial_statements "),
(r"from app\.models\.cached_financial ", "from app.models.legacy.financial.cached_financial "),
(r"from app\.models\.watchlist ", "from app.models.legacy.financial.watchlist "),
```

注意：`from app.models import User` 这种从 `__init__.py` 导入的模式不需要改（re-export 已覆盖）。只改 `from app.models.user import User` 这种直接引用子文件的模式。

运行：

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python scripts/rewrite_imports.py --dry-run
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python scripts/rewrite_imports.py
```

- [ ] **Step 10: 验证 Alembic**

```bash
cd backend
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -c "
from app.database import Base
from app.models import *
print(f'Tables registered: {len(Base.metadata.tables)}')
for t in sorted(Base.metadata.tables):
    print(f'  {t}')
"
```

Expected: 所有表都在。如果缺表，说明某个模型没被 `__init__.py` 导入。

- [ ] **Step 11: 验证测试**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
```

- [ ] **Step 12: Commit**

```bash
git add backend/app/models/ scripts/rewrite_imports.py
git add -u
git commit -m "refactor(phase5): reorganize models/ by domain with re-export compat"
```

---

### Task 6: Phase 6 — schemas/ 分组

**Files:**
- Move: `backend/app/schemas/*.py` 到子目录
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: 创建子目录**

```bash
cd backend/app/schemas
mkdir -p auth project chat ontology legacy/financial
```

- [ ] **Step 2: git mv 各域 schema 文件**

auth 域：
```bash
cd backend/app/schemas
git mv auth.py auth/auth.py
git mv user.py auth/user.py
git mv public_auth.py auth/public_auth.py
```

project 域：
```bash
git mv project.py project/project.py
git mv asset.py project/asset.py
```

chat 域：
```bash
git mv chat.py chat/chat.py
git mv agent.py chat/agent.py
git mv structured_response.py chat/structured_response.py
```

ontology 域：
```bash
git mv ontology.py ontology/ontology.py
git mv ontology_store.py ontology/ontology_store.py
git mv auto_model.py ontology/auto_model.py
```

legacy/financial 域：
```bash
git mv public_query.py legacy/financial/public_query.py
git mv watchlist.py legacy/financial/watchlist.py
```

- [ ] **Step 3: 创建各子目录 `__init__.py` 并 re-export**

每个子目录的 `__init__.py` re-export 该目录下的公开类型。

- [ ] **Step 4: 重写 schemas/__init__.py**

```python
"""Schemas package — re-exports for backward compatibility."""
from app.schemas.auth.user import User, UserCreate, UserUpdate, UserInDB
from app.schemas.project.project import Project, ProjectCreate, ProjectUpdate, ProjectWithOwner
from app.schemas.auth.auth import Token, TokenData, LoginRequest
from app.schemas.project.asset import Asset, AssetCreate, AssetUpdate, AssetWithLineage, Lineage

__all__ = [
    "User", "UserCreate", "UserUpdate", "UserInDB",
    "Project", "ProjectCreate", "ProjectUpdate", "ProjectWithOwner",
    "Token", "TokenData", "LoginRequest",
    "Asset", "AssetCreate", "AssetUpdate", "AssetWithLineage", "Lineage",
]
```

- [ ] **Step 5: 扩展 rewrite_imports.py 加 schemas 映射**

```python
# schemas domain
(r"from app\.schemas\.auth ", "from app.schemas.auth.auth "),
(r"from app\.schemas\.user ", "from app.schemas.auth.user "),
(r"from app\.schemas\.public_auth ", "from app.schemas.auth.public_auth "),
(r"from app\.schemas\.project ", "from app.schemas.project.project "),
(r"from app\.schemas\.asset ", "from app.schemas.project.asset "),
(r"from app\.schemas\.chat ", "from app.schemas.chat.chat "),
(r"from app\.schemas\.agent ", "from app.schemas.chat.agent "),
(r"from app\.schemas\.structured_response ", "from app.schemas.chat.structured_response "),
(r"from app\.schemas\.ontology_store ", "from app.schemas.ontology.ontology_store "),
(r"from app\.schemas\.ontology ", "from app.schemas.ontology.ontology "),
(r"from app\.schemas\.auto_model ", "from app.schemas.ontology.auto_model "),
(r"from app\.schemas\.public_query ", "from app.schemas.legacy.financial.public_query "),
(r"from app\.schemas\.watchlist ", "from app.schemas.legacy.financial.watchlist "),
```

运行 dry-run 后执行。

- [ ] **Step 6: 验证**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/ scripts/rewrite_imports.py
git add -u
git commit -m "refactor(phase6): reorganize schemas/ by domain"
```

---

### Task 7: Phase 7 — api/ 重组 + router 注册更新

**Files:**
- Move: `backend/app/api/*.py` 到子目录
- Modify: `backend/app/api/__init__.py` (router 注册)

当前 `api/__init__.py` 注册 17 个 router。重组后 import 路径和 router 注册都要更新。

- [ ] **Step 1: 创建子目录**

```bash
cd backend/app/api
mkdir -p auth projects chat ontology pipelines legacy/financial
```

- [ ] **Step 2: git mv auth 域**

```bash
cd backend/app/api
git mv auth.py auth/login.py
git mv api_keys.py auth/api_keys.py
git mv public_auth.py auth/public_auth.py
```

- [ ] **Step 3: git mv projects 域**

```bash
git mv projects.py projects/crud.py
git mv members.py projects/members.py
git mv assets.py projects/assets.py
git mv audit.py projects/audit.py
```

- [ ] **Step 4: git mv chat 域**

```bash
git mv chat.py chat/chat.py
git mv agent.py chat/agent.py
```

- [ ] **Step 5: git mv ontology 域**

```bash
git mv ontology_store_routes.py ontology/store.py
git mv ontology.py ontology/legacy.py
git mv semantic.py ontology/semantic.py
```

- [ ] **Step 6: git mv pipelines 域**

```bash
git mv pipelines.py pipelines/crud.py
```

- [ ] **Step 7: git mv legacy/financial 域**

```bash
git mv query.py legacy/financial/query.py
git mv datasources.py legacy/financial/datasources.py
git mv datahub.py legacy/financial/datahub.py
git mv watchlist.py legacy/financial/watchlist.py
git mv public_query.py legacy/financial/public_query.py
```

- [ ] **Step 8: 重写 api/__init__.py**

```python
"""API package."""
from fastapi import APIRouter

from app.api.auth import login, api_keys, public_auth
from app.api.projects import crud as projects_crud, members, assets, audit
from app.api.chat import chat, agent
from app.api.ontology import store as ontology_store, legacy as ontology_legacy, semantic
from app.api.pipelines import crud as pipelines_crud
from app.api.legacy.financial import query, datasources, datahub, watchlist, public_query

api_router = APIRouter()

# auth
api_router.include_router(login.router, prefix="/auth", tags=["auth"])
api_router.include_router(api_keys.router, prefix="/projects", tags=["api-keys"])
api_router.include_router(public_auth.router, prefix="/auth", tags=["public-auth"])

# projects
api_router.include_router(projects_crud.router, prefix="/projects", tags=["projects"])
api_router.include_router(members.router, tags=["members"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(audit.router, tags=["audit"])

# chat
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])

# ontology
api_router.include_router(ontology_legacy.router, prefix="/ontology", tags=["ontology"])
api_router.include_router(ontology_store.router, prefix="/ontology-store", tags=["ontology-store"])
api_router.include_router(semantic.router, prefix="", tags=["semantic"])

# pipelines
api_router.include_router(pipelines_crud.router, tags=["pipelines"])

# legacy/financial
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(datasources.router, tags=["datasources"])
api_router.include_router(datahub.router, prefix="/datahub", tags=["datahub"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(public_query.router, tags=["public-query"])
```

注意：`deps.py` 和 `public_deps.py` 留在 `api/` 根目录不动。

**重要：** `public_auth.py` 和 `public_query.py` 的 router 注册在 `app/main.py`（不在 `api/__init__.py`）。移动后需要更新 `main.py` 的 import：

```python
# main.py 中原来的：
from app.api import public_auth, public_query
# 改为：
from app.api.auth import public_auth
from app.api.legacy.financial import public_query
```

- [ ] **Step 9: 创建各子目录 `__init__.py`**

每个子目录创建空 `__init__.py`。

- [ ] **Step 10: 扩展 rewrite_imports.py 加 api 映射**

处理 api 文件内部互相引用的 import（如 `from app.api.deps import ...`）。`deps.py` 和 `public_deps.py` 没动，所以引用它们的 import 不需要改。

但 api 文件内部如果有 `from app.api.auth import ...` 这种引用，需要检查：

```bash
grep -rn "from app\.api\." backend/app/api/ --include="*.py" | grep -v __pycache__ | grep -v __init__
```

手动修复找到的引用。

- [ ] **Step 11: 验证**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -c "from app.api import api_router; print(f'Routes: {len(api_router.routes)}')"
```

Expected: 路由数量与重组前一致。

- [ ] **Step 12: Commit**

```bash
git add backend/app/api/
git add -u
git commit -m "refactor(phase7): reorganize api/ by domain, update router registration"
```

---

### Task 8: Phase 8 — configs/ + docs/ 整理

**Files:**
- Move: `configs/*.yaml` 到子目录
- Move: `docs/*.md` 到子目录
- Move: `configs/templates/*.md` 到 `docs/design/`

- [ ] **Step 1: configs/ 重组**

```bash
mkdir -p configs/legacy/financial
git mv configs/financial_stock_analysis.yaml configs/legacy/financial/
git mv configs/ppy_ontology.yaml configs/legacy/financial/
```

`configs/templates/` 已存在，不动。

- [ ] **Step 2: 修复 configs 路径引用**

```bash
grep -rn "financial_stock_analysis\|ppy_ontology" backend/ --include="*.py" -l
grep -rn "financial_stock_analysis\|ppy_ontology" backend/tests/ --include="*.py" -l
```

更新找到的路径引用（通常在 service 或 test 文件中硬编码了 `configs/financial_stock_analysis.yaml`）。

- [ ] **Step 3: docs/ 重组**

```bash
mkdir -p docs/api docs/guides docs/design
git mv docs/API_USAGE_GUIDE.md docs/api/
git mv docs/omaha-intro.md docs/guides/
git mv docs/ONTOLOGY_DEMO.md docs/guides/
git mv docs/university-talk.md docs/guides/
git mv docs/repository-structure.md docs/design/
```

如果 `configs/templates/` 下有 `.md` 文件（positioning 文档），移到 `docs/design/`：

```bash
ls configs/templates/*.md 2>/dev/null && git mv configs/templates/*.md docs/design/
```

`docs/market_analysis/` 和 `docs/superpowers/` 不动。

- [ ] **Step 4: 验证**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
git add configs/ docs/
git add -u
git commit -m "refactor(phase8): reorganize configs/ and docs/ by domain"
```

---

### Task 9: Phase 9 — 前端重组

**Files:**
- Move: `frontend/src/pages/v2/*.tsx` 到领域子目录
- Move: `frontend/src/pages/*.tsx` (v1) 到 `pages/legacy/`
- Move: `frontend/src/components/map/` 到 `components/legacy/`
- Move: `frontend/src/components/Layout/` 到 `components/layout/`
- Move: 共享组件到 `components/shared/`

`frontend/src/layouts/`、`services/`、`hooks/`、`contexts/`、`components/ui/`、`components/chat/` 不动。

- [ ] **Step 1: 创建前端子目录**

```bash
cd frontend/src
mkdir -p pages/assistant pages/ontology pages/dashboard pages/apps pages/settings pages/legacy
mkdir -p components/legacy components/layout components/shared
```

- [ ] **Step 2: 移动 v2 pages 到领域目录**

```bash
cd frontend/src/pages
git mv v2/AssistantPage.tsx assistant/
git mv v2/ModelingPage.tsx ontology/
git mv v2/OntologyBrowser.tsx ontology/
git mv v2/OntologyGraph.tsx ontology/
git mv v2/DashboardPage.tsx dashboard/
git mv v2/AppsPage.tsx apps/
git mv v2/DatasourcePage.tsx apps/
git mv v2/PipelinesPage.tsx apps/
git mv v2/ApiKeysPage.tsx settings/
git mv v2/AuditPage.tsx settings/
git mv v2/SettingsPage.tsx settings/
```

删除空的 `v2/` 目录：

```bash
rmdir v2 2>/dev/null || rm -rf v2
```

- [ ] **Step 3: 移动 v1 pages 到 legacy/**

```bash
cd frontend/src/pages
git mv ObjectExplorer.tsx legacy/
git mv OntologyEditor.tsx legacy/
git mv OntologyMap.tsx legacy/
git mv AggregateQuery.tsx legacy/
git mv Explorer.tsx legacy/
git mv QueryBuilder.tsx legacy/
git mv QueryHistory.tsx legacy/
git mv DatasourceManager.tsx legacy/
git mv PipelineManager.tsx legacy/
git mv Watchlist.tsx legacy/
git mv AuditLogViewer.tsx legacy/
git mv MembersManager.tsx legacy/
```

保留在根目录的页面（通用）：`Login.tsx`、`Register.tsx`、`ProjectList.tsx`、`Settings.tsx`、`ChatAgent.tsx`、`ChatPage.tsx`、`ChatWithSessions.tsx`。

- [ ] **Step 4: 移动组件**

```bash
cd frontend/src/components
git mv map legacy
git mv Layout layout
git mv PrivateRoute.tsx shared/
git mv RequireProject.tsx shared/
git mv ApiKeyManager.tsx shared/
git mv QueryChart.tsx shared/
```

- [ ] **Step 5: 更新前端 import 路径**

搜索所有受影响的 import：

```bash
grep -rn "from.*pages/v2/" frontend/src/ --include="*.tsx" --include="*.ts" -l
grep -rn "from.*components/map/" frontend/src/ --include="*.tsx" --include="*.ts" -l
grep -rn "from.*components/Layout/" frontend/src/ --include="*.tsx" --include="*.ts" -l
grep -rn "from.*components/PrivateRoute" frontend/src/ --include="*.tsx" --include="*.ts" -l
grep -rn "from.*components/RequireProject" frontend/src/ --include="*.tsx" --include="*.ts" -l
grep -rn "from.*components/ApiKeyManager" frontend/src/ --include="*.tsx" --include="*.ts" -l
grep -rn "from.*components/QueryChart" frontend/src/ --include="*.tsx" --include="*.ts" -l
```

逐个更新 import 路径。关键文件：
- `frontend/src/App.tsx`（路由定义，引用所有 page 组件）
- `frontend/src/layouts/navConfig.ts`（如果引用了 page 路径）
- v1 `OntologyMap.tsx` 内部引用 `components/map/` → 改为 `components/legacy/`

- [ ] **Step 6: 验证前端构建**

```bash
cd frontend && npm run build
```

Expected: 构建成功，无错误。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git add -u
git commit -m "refactor(phase9): reorganize frontend pages/ and components/ by domain"
```

---

### Task 10: Phase 10 — 全套验证 + 收尾

**Files:**
- Modify: `CLAUDE.md` (更新目录结构文档)
- Modify: `docs/design/repository-structure.md` (如存在)

- [ ] **Step 1: 全套后端测试**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest backend/tests/ -q --tb=line
```

Expected: 与 Phase 0 基线一致（436 passed / 9 failed），零新增回归。

- [ ] **Step 2: 启动检查**

```bash
cd backend
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -c "from app.main import app; print('Startup OK')"
```

- [ ] **Step 3: 前端构建**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: 更新 CLAUDE.md 目录结构**

更新 CLAUDE.md 中的 "Backend Structure" 和 "Frontend Structure" 部分，反映新的领域分组目录结构。

- [ ] **Step 5: 清理 rewrite_imports.py**

确认脚本不再需要后可以保留在 `scripts/` 作为参考，或删除：

```bash
git rm scripts/rewrite_imports.py  # 如果不再需要
```

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git add -u
git commit -m "refactor(phase10): final validation + update docs"
```

- [ ] **Step 7: 使用 finishing-a-development-branch 完成分支**

调用 `superpowers:finishing-a-development-branch` skill 处理合并/PR。
