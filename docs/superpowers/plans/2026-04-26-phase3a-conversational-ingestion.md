# Phase 3a: Conversational Data Ingestion + Cleaning — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Users can upload Excel/CSV files through Agent conversation, get automatic data quality assessment and cleaning, with rich UI components (option cards, quality panels, file upload) in the chat interface.

**Architecture:** Extend existing AgentToolkit with new tools (upload_file, assess_quality, clean_data). Add structured response types to chat API so the frontend can render rich components (OptionCards, FileUpload, QualityPanel). Add `setup_stage` to Project model for onboarding state tracking. Reuse existing CSVConnector for file ingestion.

**Tech Stack:** FastAPI, SQLAlchemy, pandas (Excel parsing), openpyxl, React 18, TypeScript, Tailwind CSS

---

## File Structure

### Backend — New Files
- `backend/app/services/data_cleaner.py` — Data quality assessment and cleaning engine
- `backend/app/schemas/structured_response.py` — Pydantic models for structured Agent responses
- `backend/tests/test_data_cleaner.py` — Unit tests for cleaning engine
- `backend/tests/test_upload_tool.py` — Tests for upload_file tool
- `backend/tests/test_structured_response.py` — Tests for structured response schemas
- `backend/tests/test_setup_stage.py` — Tests for setup_stage state transitions

### Backend — Modified Files
- `backend/app/models/project.py` — Add `setup_stage` field
- `backend/app/services/agent_tools.py` — Add upload_file, assess_quality, clean_data tools
- `backend/app/services/agent.py` — Inject setup_stage context into system prompt
- `backend/app/schemas/chat.py` — Extend SendMessageResponse with structured content
- `backend/app/api/chat.py` — Handle file upload in chat endpoint

### Frontend — New Files
- `frontend/src/components/chat/OptionCards.tsx` — Clickable option cards
- `frontend/src/components/chat/FileUploadZone.tsx` — Drag-and-drop file upload in chat
- `frontend/src/components/chat/QualityPanel.tsx` — Data quality report panel
- `frontend/src/components/chat/StructuredMessage.tsx` — Router for structured message types

### Frontend — Modified Files
- `frontend/src/components/chat/ChatMessage.tsx` — Render structured messages
- `frontend/src/pages/ChatAgent.tsx` — Handle file upload and option selection
- `frontend/src/services/chatApi.ts` — Add file upload API method
- `frontend/src/types/chat.ts` — Add structured response types

### Database Migration
- `backend/alembic/versions/xxx_add_setup_stage.py` — Add setup_stage to projects

---

### Task 1: Add `setup_stage` to Project Model

**Files:**
- Modify: `backend/app/models/project.py`
- Create: `backend/alembic/versions/xxx_add_setup_stage.py`
- Create: `backend/tests/test_setup_stage.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_setup_stage.py
import pytest
from app.models.project import Project

def test_project_has_setup_stage_default():
    p = Project(name="test", owner_id=1)
    assert p.setup_stage == "idle"

def test_project_setup_stage_values():
    valid = ["idle", "connecting", "cleaning", "modeling", "ready"]
    for stage in valid:
        p = Project(name="test", owner_id=1, setup_stage=stage)
        assert p.setup_stage == stage
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_setup_stage.py -v`
Expected: FAIL — `Project` has no `setup_stage` attribute

- [ ] **Step 3: Add setup_stage to Project model**

```python
# backend/app/models/project.py — add to Project class
setup_stage = Column(String(20), nullable=False, default="idle", server_default="idle")
```

- [ ] **Step 4: Create Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add setup_stage to projects"`

- [ ] **Step 5: Run migration**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_setup_stage.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/project.py backend/alembic/versions/ backend/tests/test_setup_stage.py
git commit -m "feat: add setup_stage to Project model"
```

---

### Task 2: Structured Response Schema

**Files:**
- Create: `backend/app/schemas/structured_response.py`
- Create: `backend/tests/test_structured_response.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_structured_response.py
import pytest
from app.schemas.structured_response import (
    TextResponse, OptionsResponse, PanelResponse, Option, StructuredContent
)

def test_text_response():
    r = TextResponse(content="hello")
    assert r.type == "text"
    assert r.content == "hello"

def test_options_response():
    r = OptionsResponse(
        content="选择数据源类型",
        options=[
            Option(label="Excel/CSV 文件", value="excel"),
            Option(label="数据库", value="database"),
        ]
    )
    assert r.type == "options"
    assert len(r.options) == 2
    assert r.options[0].value == "excel"

def test_panel_response():
    r = PanelResponse(
        content="数据质量报告",
        panel_type="quality_report",
        data={"score": 67, "issues": []}
    )
    assert r.type == "panel"
    assert r.panel_type == "quality_report"
    assert r.data["score"] == 67

def test_structured_content_list():
    items = [
        TextResponse(content="分析完成"),
        PanelResponse(content="结果", panel_type="quality_report", data={"score": 94}),
    ]
    sc = StructuredContent(items=items)
    assert len(sc.items) == 2
    assert sc.items[0].type == "text"
    assert sc.items[1].type == "panel"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_structured_response.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement structured response schemas**

```python
# backend/app/schemas/structured_response.py
from typing import Any, Literal, Union
from pydantic import BaseModel

class Option(BaseModel):
    label: str
    value: str

class TextResponse(BaseModel):
    type: Literal["text"] = "text"
    content: str

class OptionsResponse(BaseModel):
    type: Literal["options"] = "options"
    content: str
    options: list[Option]

class PanelResponse(BaseModel):
    type: Literal["panel"] = "panel"
    content: str
    panel_type: str
    data: dict[str, Any]

class FileUploadRequest(BaseModel):
    type: Literal["file_upload"] = "file_upload"
    content: str
    accept: str = ".xlsx,.xls,.csv"
    multiple: bool = True

StructuredItem = Union[TextResponse, OptionsResponse, PanelResponse, FileUploadRequest]

class StructuredContent(BaseModel):
    items: list[StructuredItem]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_structured_response.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/structured_response.py backend/tests/test_structured_response.py
git commit -m "feat: add structured response schemas for rich chat UI"
```

---

### Task 3: Data Cleaner Service

**Files:**
- Create: `backend/app/services/data_cleaner.py`
- Create: `backend/tests/test_data_cleaner.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_data_cleaner.py
import pytest
import pandas as pd
from app.services.data_cleaner import DataCleaner, QualityReport, QualityIssue

def test_assess_detects_duplicate_rows():
    df = pd.DataFrame({"name": ["张三", "张三", "李四"], "amount": [100, 100, 200]})
    report = DataCleaner.assess({"customers": df})
    issues = [i for i in report.issues if i.issue_type == "duplicate_rows"]
    assert len(issues) == 1
    assert issues[0].table == "customers"
    assert issues[0].count == 1

def test_assess_detects_missing_values():
    df = pd.DataFrame({"name": ["张三", None, "李四"], "amount": [100, 200, None]})
    report = DataCleaner.assess({"orders": df})
    issues = [i for i in report.issues if i.issue_type == "missing_values"]
    assert len(issues) == 2  # one per column with nulls

def test_assess_detects_inconsistent_dates():
    df = pd.DataFrame({"date": ["2024/3/5", "3月5号", "2024-03-06", "45356"]})
    report = DataCleaner.assess({"orders": df})
    issues = [i for i in report.issues if i.issue_type == "inconsistent_format"]
    assert len(issues) >= 1

def test_assess_quality_score():
    df = pd.DataFrame({"name": ["张三", "李四"], "amount": [100, 200]})
    report = DataCleaner.assess({"clean_table": df})
    assert report.score >= 90

def test_clean_removes_duplicate_rows():
    df = pd.DataFrame({"name": ["张三", "张三", "李四"], "amount": [100, 100, 200]})
    result = DataCleaner.clean({"t": df}, auto_rules=["duplicate_rows"])
    assert len(result["t"]) == 2

def test_clean_standardizes_dates():
    df = pd.DataFrame({"date": ["2024/3/5", "2024-03-06"]})
    result = DataCleaner.clean({"t": df}, auto_rules=["standardize_dates"])
    assert result["t"]["date"].iloc[0] == "2024-03-05"
    assert result["t"]["date"].iloc[1] == "2024-03-06"

def test_clean_strips_whitespace():
    df = pd.DataFrame({"name": [" 张三 ", "李四  "]})
    result = DataCleaner.clean({"t": df}, auto_rules=["strip_whitespace"])
    assert result["t"]["name"].iloc[0] == "张三"
    assert result["t"]["name"].iloc[1] == "李四"

def test_quality_report_to_dict():
    report = QualityReport(
        score=67,
        issues=[QualityIssue(table="t", column="name", issue_type="duplicate_rows", count=5, examples=["张三"], suggestion="去重")]
    )
    d = report.to_dict()
    assert d["score"] == 67
    assert len(d["issues"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_data_cleaner.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement DataCleaner**

```python
# backend/app/services/data_cleaner.py
from dataclasses import dataclass, field, asdict
import pandas as pd
import re

@dataclass
class QualityIssue:
    table: str
    column: str | None
    issue_type: str  # duplicate_rows, missing_values, inconsistent_format, non_numeric
    count: int
    examples: list[str]
    suggestion: str
    auto_fixable: bool = True

@dataclass
class QualityReport:
    score: int
    issues: list[QualityIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"score": self.score, "issues": [asdict(i) for i in self.issues]}


class DataCleaner:
    @staticmethod
    def assess(tables: dict[str, pd.DataFrame]) -> QualityReport:
        issues: list[QualityIssue] = []
        total_cells = 0
        problem_cells = 0

        for table_name, df in tables.items():
            total_cells += df.size

            # Duplicate rows
            dup_count = df.duplicated().sum()
            if dup_count > 0:
                problem_cells += dup_count * len(df.columns)
                issues.append(QualityIssue(
                    table=table_name, column=None,
                    issue_type="duplicate_rows", count=int(dup_count),
                    examples=[], suggestion="删除重复行",
                ))

            for col in df.columns:
                # Missing values
                null_count = int(df[col].isna().sum())
                if null_count > 0:
                    problem_cells += null_count
                    issues.append(QualityIssue(
                        table=table_name, column=col,
                        issue_type="missing_values", count=null_count,
                        examples=[], suggestion=f"填充或删除 {null_count} 条空值",
                        auto_fixable=False,
                    ))

                # Inconsistent date formats
                if df[col].dtype == object:
                    vals = df[col].dropna().astype(str)
                    date_patterns = [
                        r"\d{4}[/-]\d{1,2}[/-]\d{1,2}",
                        r"\d{1,2}月\d{1,2}[号日]",
                        r"^\d{5}$",  # Excel serial date
                    ]
                    matched = set()
                    for v in vals:
                        for i, pat in enumerate(date_patterns):
                            if re.search(pat, v):
                                matched.add(i)
                    if len(matched) > 1:
                        problem_cells += len(vals)
                        issues.append(QualityIssue(
                            table=table_name, column=col,
                            issue_type="inconsistent_format", count=len(vals),
                            examples=vals.head(3).tolist(),
                            suggestion="统一为 YYYY-MM-DD 格式",
                        ))

        score = 100 if total_cells == 0 else max(0, 100 - int(problem_cells / total_cells * 100))
        return QualityReport(score=score, issues=issues)

    @staticmethod
    def clean(tables: dict[str, pd.DataFrame], auto_rules: list[str]) -> dict[str, pd.DataFrame]:
        result = {}
        for name, df in tables.items():
            df = df.copy()
            if "duplicate_rows" in auto_rules:
                df = df.drop_duplicates()
            if "strip_whitespace" in auto_rules:
                for col in df.select_dtypes(include=["object"]).columns:
                    df[col] = df[col].str.strip()
            if "standardize_dates" in auto_rules:
                for col in df.select_dtypes(include=["object"]).columns:
                    try:
                        parsed = pd.to_datetime(df[col], format="mixed", dayfirst=False)
                        df[col] = parsed.dt.strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        pass
            result[name] = df
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_data_cleaner.py -v`
Expected: PASS (some date tests may need adjustment based on pandas version)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/data_cleaner.py backend/tests/test_data_cleaner.py
git commit -m "feat: add DataCleaner service for quality assessment and cleaning"
```

---

### Task 4: Agent Tools — upload_file, assess_quality, clean_data

**Files:**
- Modify: `backend/app/services/agent_tools.py`
- Create: `backend/tests/test_upload_tool.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_upload_tool.py
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import json
from app.services.agent_tools import AgentToolkit

@pytest.fixture
def toolkit():
    mock_omaha = MagicMock()
    return AgentToolkit(omaha_service=mock_omaha)

def test_toolkit_has_new_tools(toolkit):
    defs = toolkit.get_tool_definitions()
    names = [d["name"] for d in defs]
    assert "upload_file" in names
    assert "assess_quality" in names
    assert "clean_data" in names

def test_assess_quality_returns_report(toolkit):
    # Mock: project has uploaded tables stored in toolkit context
    toolkit._uploaded_tables = {
        "orders": pd.DataFrame({"name": ["张三", "张三"], "amount": [100, 100]})
    }
    result = toolkit.execute_tool("assess_quality", {})
    assert result["success"] is True
    assert "score" in result["data"]
    assert "issues" in result["data"]

def test_clean_data_applies_rules(toolkit):
    toolkit._uploaded_tables = {
        "orders": pd.DataFrame({"name": [" 张三 ", "李四  "], "amount": [100, 200]})
    }
    result = toolkit.execute_tool("clean_data", {"rules": ["strip_whitespace", "duplicate_rows"]})
    assert result["success"] is True
    assert result["data"]["orders_cleaned"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_upload_tool.py -v`
Expected: FAIL — tools not registered

- [ ] **Step 3: Add new tools to AgentToolkit**

Add to `backend/app/services/agent_tools.py` in `__init__`:

```python
# In __init__, add to self._tools:
"upload_file": self._upload_file,
"assess_quality": self._assess_quality,
"clean_data": self._clean_data,
```

Add to `get_tool_definitions()` return list:

```python
{
    "name": "upload_file",
    "description": "用户上传了文件后调用此工具，解析 Excel/CSV 文件并存入平台。不要主动调用，等用户上传文件后系统会自动触发。",
    "parameters": {
        "file_path": {"type": "string", "description": "上传文件的服务器路径", "required": True},
        "table_name": {"type": "string", "description": "存储的表名", "required": True},
    }
},
{
    "name": "assess_quality",
    "description": "评估已上传数据的质量，返回质量评分和问题清单。在用户上传文件后自动调用。",
    "parameters": {}
},
{
    "name": "clean_data",
    "description": "对已上传的数据执行清洗操作。rules 可选值：duplicate_rows, strip_whitespace, standardize_dates",
    "parameters": {
        "rules": {"type": "array", "description": "要执行的清洗规则列表", "required": True},
    }
},
```

Add handler methods:

```python
def _upload_file(self, params: dict) -> dict:
    from app.connectors.csv_connector import CSVConnector
    file_path = params["file_path"]
    table_name = params["table_name"]
    try:
        connector = CSVConnector({})
        columns = connector.ingest(file_path, table_name)
        df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
        if not hasattr(self, '_uploaded_tables'):
            self._uploaded_tables = {}
        self._uploaded_tables[table_name] = df
        return {
            "success": True,
            "data": {
                "table_name": table_name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": [{"name": c, "type": str(df[c].dtype)} for c in df.columns],
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def _assess_quality(self, params: dict) -> dict:
    from app.services.data_cleaner import DataCleaner
    if not hasattr(self, '_uploaded_tables') or not self._uploaded_tables:
        return {"success": False, "error": "没有已上传的数据，请先上传文件"}
    report = DataCleaner.assess(self._uploaded_tables)
    return {"success": True, "data": report.to_dict()}

def _clean_data(self, params: dict) -> dict:
    from app.services.data_cleaner import DataCleaner
    if not hasattr(self, '_uploaded_tables') or not self._uploaded_tables:
        return {"success": False, "error": "没有已上传的数据"}
    rules = params.get("rules", [])
    cleaned = DataCleaner.clean(self._uploaded_tables, auto_rules=rules)
    summary = {f"{name}_cleaned": len(df) for name, df in cleaned.items()}
    self._uploaded_tables = cleaned
    return {"success": True, "data": summary}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_upload_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_tools.py backend/tests/test_upload_tool.py
git commit -m "feat: add upload_file, assess_quality, clean_data tools to AgentToolkit"
```

---

### Task 5: Extend Chat API for Structured Responses and File Upload

**Files:**
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/api/chat.py`

- [ ] **Step 1: Extend SendMessageResponse schema**

In `backend/app/schemas/chat.py`, add:

```python
from typing import Any

class StructuredItem(BaseModel):
    type: str  # "text", "options", "panel", "file_upload"
    content: str
    options: Optional[List[Dict[str, str]]] = None
    panel_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    accept: Optional[str] = None
    multiple: Optional[bool] = None

class SendMessageResponse(BaseModel):
    message: str
    data_table: Optional[List[Dict[str, Any]]] = None
    chart_config: Optional[Dict[str, Any]] = None
    sql: Optional[str] = None
    structured: Optional[List[StructuredItem]] = None  # NEW
    setup_stage: Optional[str] = None  # NEW
```

- [ ] **Step 2: Add file upload endpoint to chat API**

In `backend/app/api/chat.py`, add:

```python
@router.post("/chat/{project_id}/sessions/{session_id}/upload")
async def upload_file_in_chat(
    project_id: int,
    session_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    upload_dir = Path(f"data/uploads/{project_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    return {"success": True, "file_path": str(file_path), "filename": file.filename}
```

- [ ] **Step 3: Run existing chat tests to verify no regression**

Run: `cd backend && python -m pytest tests/test_api_chat.py -v`
Expected: PASS (existing tests still work)

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/chat.py backend/app/api/chat.py
git commit -m "feat: extend chat API with structured responses and file upload"
```

---

### Task 6: Agent System Prompt — Setup Stage Awareness

**Files:**
- Modify: `backend/app/services/agent.py`

- [ ] **Step 1: Add setup_stage context to system prompt**

In `backend/app/services/agent.py`, modify `build_system_prompt()`:

```python
def build_system_prompt(self, setup_stage: str = "ready") -> str:
    objects_ctx = self._format_objects()
    health_ctx = self._format_health_rules()
    goals_ctx = self._format_goals()
    knowledge_ctx = self._format_knowledge()
    tools_ctx = self._format_tools()
    onboarding_ctx = self._format_onboarding(setup_stage)

    return SYSTEM_PROMPT_TEMPLATE.format(
        objects_context=objects_ctx,
        health_rules_context=health_ctx,
        goals_context=goals_ctx,
        knowledge_context=knowledge_ctx,
        tools_context=tools_ctx,
        onboarding_context=onboarding_ctx,
    )
```

Add the onboarding formatter:

```python
ONBOARDING_PROMPTS = {
    "idle": """## 当前状态：新用户引导
用户刚创建项目，还没有接入数据。你的任务是引导用户完成数据接入。
1. 先问用户是什么行业的
2. 再问用什么方式管理数据（Excel/数据库/SaaS软件）
3. 引导用户上传文件或填写连接信息
用业务语言，不要用技术术语。""",

    "connecting": """## 当前状态：数据接入中
用户正在接入数据源。如果上传了文件，自动调用 assess_quality 评估数据质量。""",

    "cleaning": """## 当前状态：数据清洗中
数据已接入，正在清洗。展示质量问题，引导用户确认清洗方案。""",

    "modeling": """## 当前状态：语义建模中
数据已清洗，正在构建本体。引导用户确认业务对象和字段含义。""",

    "ready": """## 当前状态：就绪
数据已就绪，用户可以自由提问。主动给出示例问题帮助用户开始。""",
}

def _format_onboarding(self, setup_stage: str) -> str:
    return ONBOARDING_PROMPTS.get(setup_stage, ONBOARDING_PROMPTS["ready"])
```

Update `SYSTEM_PROMPT_TEMPLATE` to include `{onboarding_context}`.

- [ ] **Step 2: Update ChatService to pass setup_stage**

In `backend/app/services/chat.py`, in `send_message()`, read project.setup_stage and pass it to agent:

```python
project = db.query(Project).filter(Project.id == project_id).first()
setup_stage = project.setup_stage or "idle"
# Pass to agent.build_system_prompt(setup_stage=setup_stage)
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/ -k "chat" -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/agent.py backend/app/services/chat.py
git commit -m "feat: add setup_stage awareness to Agent system prompt"
```

---

### Task 7: Frontend — Structured Message Types

**Files:**
- Modify: `frontend/src/types/chat.ts`
- Create: `frontend/src/components/chat/StructuredMessage.tsx`

- [ ] **Step 1: Add structured types**

In `frontend/src/types/chat.ts`:

```typescript
export interface StructuredItem {
  type: 'text' | 'options' | 'panel' | 'file_upload';
  content: string;
  options?: { label: string; value: string }[];
  panel_type?: string;
  data?: Record<string, any>;
  accept?: string;
  multiple?: boolean;
}

export interface SendMessageResponse {
  message: string;
  data_table: Record<string, any>[] | null;
  chart_config: Record<string, any> | null;
  sql: string | null;
  structured: StructuredItem[] | null;
  setup_stage: string | null;
}
```

- [ ] **Step 2: Create StructuredMessage router component**

```tsx
// frontend/src/components/chat/StructuredMessage.tsx
import { StructuredItem } from '../../types/chat';
import { OptionCards } from './OptionCards';
import { QualityPanel } from './QualityPanel';
import { FileUploadZone } from './FileUploadZone';

interface Props {
  items: StructuredItem[];
  onOptionSelect?: (value: string) => void;
  onFileUpload?: (files: FileList) => void;
}

export function StructuredMessage({ items, onOptionSelect, onFileUpload }: Props) {
  return (
    <div className="space-y-3">
      {items.map((item, i) => {
        switch (item.type) {
          case 'text':
            return <p key={i} className="text-sm whitespace-pre-wrap">{item.content}</p>;
          case 'options':
            return (
              <div key={i}>
                <p className="text-sm mb-2">{item.content}</p>
                <OptionCards options={item.options || []} onSelect={onOptionSelect} />
              </div>
            );
          case 'panel':
            if (item.panel_type === 'quality_report') {
              return <QualityPanel key={i} data={item.data || {}} />;
            }
            return <p key={i} className="text-sm">{item.content}</p>;
          case 'file_upload':
            return (
              <div key={i}>
                <p className="text-sm mb-2">{item.content}</p>
                <FileUploadZone
                  accept={item.accept || '.xlsx,.xls,.csv'}
                  multiple={item.multiple ?? true}
                  onUpload={onFileUpload}
                />
              </div>
            );
          default:
            return <p key={i} className="text-sm">{item.content}</p>;
        }
      })}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/chat.ts frontend/src/components/chat/StructuredMessage.tsx
git commit -m "feat: add structured message types and router component"
```

---

### Task 8: Frontend — OptionCards Component

**Files:**
- Create: `frontend/src/components/chat/OptionCards.tsx`

- [ ] **Step 1: Implement OptionCards**

```tsx
// frontend/src/components/chat/OptionCards.tsx
interface Props {
  options: { label: string; value: string }[];
  onSelect?: (value: string) => void;
}

export function OptionCards({ options, onSelect }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onSelect?.(opt.value)}
          className="px-4 py-2 rounded-lg border border-gray-600 bg-gray-800 hover:bg-gray-700 text-sm text-gray-200 transition-colors"
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/OptionCards.tsx
git commit -m "feat: add OptionCards chat component"
```

---

### Task 9: Frontend — FileUploadZone Component

**Files:**
- Create: `frontend/src/components/chat/FileUploadZone.tsx`

- [ ] **Step 1: Implement FileUploadZone**

```tsx
// frontend/src/components/chat/FileUploadZone.tsx
import { useCallback, useRef, useState } from 'react';

interface Props {
  accept: string;
  multiple: boolean;
  onUpload?: (files: FileList) => void;
}

export function FileUploadZone({ accept, multiple, onUpload }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      onUpload?.(e.dataTransfer.files);
    }
  }, [onUpload]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload?.(e.target.files);
    }
  }, [onUpload]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
        dragOver ? 'border-blue-400 bg-blue-900/20' : 'border-gray-600 hover:border-gray-500'
      }`}
    >
      <p className="text-sm text-gray-400">拖拽文件到这里，或点击选择文件</p>
      <p className="text-xs text-gray-500 mt-1">支持 Excel (.xlsx, .xls) 和 CSV 文件</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleChange}
        className="hidden"
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/FileUploadZone.tsx
git commit -m "feat: add FileUploadZone chat component"
```

---

### Task 10: Frontend — QualityPanel Component

**Files:**
- Create: `frontend/src/components/chat/QualityPanel.tsx`

- [ ] **Step 1: Implement QualityPanel**

```tsx
// frontend/src/components/chat/QualityPanel.tsx
interface QualityIssue {
  table: string;
  column: string | null;
  issue_type: string;
  count: number;
  examples: string[];
  suggestion: string;
  auto_fixable: boolean;
}

interface Props {
  data: {
    score: number;
    issues: QualityIssue[];
  };
  onAutoFix?: () => void;
}

const ISSUE_LABELS: Record<string, string> = {
  duplicate_rows: '重复行',
  missing_values: '缺失值',
  inconsistent_format: '格式不一致',
  non_numeric: '非数字内容',
};

function scoreColor(score: number): string {
  if (score >= 90) return 'text-green-400';
  if (score >= 70) return 'text-yellow-400';
  return 'text-red-400';
}

export function QualityPanel({ data, onAutoFix }: Props) {
  const autoFixable = data.issues.filter((i) => i.auto_fixable);
  const needsConfirm = data.issues.filter((i) => !i.auto_fixable);

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-300">数据质量评分</span>
        <span className={`text-2xl font-bold ${scoreColor(data.score)}`}>
          {data.score}/100
        </span>
      </div>

      {data.issues.length === 0 ? (
        <p className="text-sm text-green-400">数据质量良好，无需清洗</p>
      ) : (
        <div className="space-y-2">
          {data.issues.map((issue, i) => (
            <div key={i} className="text-sm border-l-2 border-yellow-500 pl-3 py-1">
              <p className="text-gray-200">
                {ISSUE_LABELS[issue.issue_type] || issue.issue_type}
                {issue.column && ` · ${issue.table}.${issue.column}`}
                {!issue.column && ` · ${issue.table}`}
                <span className="text-gray-400 ml-2">({issue.count} 处)</span>
              </p>
              {issue.examples.length > 0 && (
                <p className="text-gray-500 text-xs mt-0.5">
                  例：{issue.examples.slice(0, 3).join(' / ')}
                </p>
              )}
              <p className="text-gray-400 text-xs">{issue.suggestion}</p>
            </div>
          ))}
        </div>
      )}

      {autoFixable.length > 0 && (
        <button
          onClick={onAutoFix}
          className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm text-white transition-colors"
        >
          一键修复 {autoFixable.length} 个可自动处理的问题
        </button>
      )}

      {needsConfirm.length > 0 && (
        <p className="text-xs text-gray-500">
          还有 {needsConfirm.length} 个问题需要你确认处理方式
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/QualityPanel.tsx
git commit -m "feat: add QualityPanel chat component"
```

---

### Task 11: Frontend — Integrate Structured Messages into Chat

**Files:**
- Modify: `frontend/src/components/chat/ChatMessage.tsx`
- Modify: `frontend/src/pages/ChatAgent.tsx`
- Modify: `frontend/src/services/chatApi.ts`

- [ ] **Step 1: Update ChatMessage to render structured content**

```tsx
// frontend/src/components/chat/ChatMessage.tsx
import { cn } from '../../utils/cn';
import { StructuredMessage } from './StructuredMessage';
import type { StructuredItem } from '../../types/chat';

interface ChatMessageProps {
  message: {
    role: string;
    content: string;
    structured?: StructuredItem[] | null;
  };
  onOptionSelect?: (value: string) => void;
  onFileUpload?: (files: FileList) => void;
  onAutoFix?: () => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message, onOptionSelect, onFileUpload, onAutoFix
}) => {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex mb-3', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[70%] rounded-lg px-4 py-2.5',
        isUser ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-200'
      )}>
        {message.structured && message.structured.length > 0 ? (
          <StructuredMessage
            items={message.structured}
            onOptionSelect={onOptionSelect}
            onFileUpload={onFileUpload}
          />
        ) : (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        )}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Add file upload method to chatApi**

In `frontend/src/services/chatApi.ts`:

```typescript
async uploadFile(
  projectId: number,
  sessionId: number,
  file: File
): Promise<{ success: boolean; file_path: string; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post(
    `/chat/${projectId}/sessions/${sessionId}/upload`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return res.data;
},
```

- [ ] **Step 3: Handle file upload and option selection in ChatAgent**

In `frontend/src/pages/ChatAgent.tsx`, add handlers:

```typescript
const handleOptionSelect = useCallback(async (value: string) => {
  // Send the selected option as a user message
  await handleSend(value);
}, [handleSend]);

const handleFileUpload = useCallback(async (files: FileList) => {
  if (!sessionId) return;
  for (const file of Array.from(files)) {
    const result = await chatApi.uploadFile(projectId, sessionId, file);
    if (result.success) {
      await handleSend(`我上传了文件：${result.filename}`);
    }
  }
}, [projectId, sessionId, handleSend]);
```

Pass these handlers to ChatMessage components in the render.

- [ ] **Step 4: Build frontend to verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no type errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/chat/ChatMessage.tsx frontend/src/pages/ChatAgent.tsx frontend/src/services/chatApi.ts
git commit -m "feat: integrate structured messages, file upload, and option selection into chat UI"
```

---

### Task 12: Integration Test — Full Onboarding Flow

**Files:**
- Create: `backend/tests/test_onboarding_flow.py`

- [ ] **Step 1: Write integration test**

```python
# backend/tests/test_onboarding_flow.py
import pytest
from unittest.mock import patch, MagicMock
from app.models.project import Project
from app.services.agent_tools import AgentToolkit
from app.services.data_cleaner import DataCleaner
import pandas as pd

def test_full_onboarding_flow():
    """Test the complete flow: upload → assess → clean → stage transitions"""
    # Setup
    mock_omaha = MagicMock()
    toolkit = AgentToolkit(omaha_service=mock_omaha)

    # Step 1: Upload file
    test_df = pd.DataFrame({
        "客户": ["张三", " 张三 ", "李四", "李四"],
        "金额": [100, 100, 200, 300],
        "日期": ["2024/3/5", "2024-03-05", "2024/3/6", "2024-03-07"],
    })
    with patch("pandas.read_excel", return_value=test_df):
        with patch("app.connectors.csv_connector.CSVConnector.ingest"):
            result = toolkit.execute_tool("upload_file", {
                "file_path": "/tmp/test.xlsx",
                "table_name": "orders"
            })
    assert result["success"] is True
    assert result["data"]["row_count"] == 4

    # Step 2: Assess quality
    result = toolkit.execute_tool("assess_quality", {})
    assert result["success"] is True
    assert result["data"]["score"] < 100  # Should detect issues
    assert len(result["data"]["issues"]) > 0

    # Step 3: Clean data
    result = toolkit.execute_tool("clean_data", {
        "rules": ["duplicate_rows", "strip_whitespace", "standardize_dates"]
    })
    assert result["success"] is True

    # Step 4: Re-assess — should be cleaner
    result = toolkit.execute_tool("assess_quality", {})
    assert result["success"] is True
    assert result["data"]["score"] > 80

def test_setup_stage_transitions():
    """Test that setup_stage transitions correctly"""
    project = Project(name="test", owner_id=1)
    assert project.setup_stage == "idle"

    project.setup_stage = "connecting"
    assert project.setup_stage == "connecting"

    project.setup_stage = "cleaning"
    assert project.setup_stage == "cleaning"

    project.setup_stage = "ready"
    assert project.setup_stage == "ready"
```

- [ ] **Step 2: Run integration test**

Run: `cd backend && python -m pytest tests/test_onboarding_flow.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `cd backend && python -m pytest tests/ -v --tb=short`
Expected: No new failures beyond the 8 pre-existing ones

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_onboarding_flow.py
git commit -m "test: add integration test for full onboarding flow"
```

- [ ] **Step 5: Build frontend one final time**

Run: `cd frontend && npm run build`
Expected: Build succeeds
