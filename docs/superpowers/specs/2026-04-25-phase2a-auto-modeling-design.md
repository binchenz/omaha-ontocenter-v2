# Phase 2a: AI自动建模 — 设计文档

## 1. 目标

让用户连接SQL数据源后，系统自动扫描表结构、AI推断业务含义、生成ontology到数据库。用户只需确认和微调，不需要手写YAML。

## 2. 用户流程

```
1. 用户选择已配置的数据源（DatasourceManager中已有）
2. 系统扫描所有表 → 返回表名、字段、行数、采样值
3. 用户勾选要建模的表
4. AI逐表推断 → 业务含义、字段语义类型、计算属性建议
5. 代码FK匹配 + AI辅助 → 推断表间关系
6. 展示完整ontology草稿 → 用户确认/微调
7. 写入DB → 完成
```

## 3. 架构

```
┌─────────────────────────────────────────┐
│  API层 (ontology_store_routes.py)        │
│  POST /scan    — 扫描表结构              │
│  POST /infer   — AI推断                 │
│  POST /confirm — 写入DB                 │
├─────────────────────────────────────────┤
│  SchemaScanner                           │
│  SQLAlchemy inspect → 表列表、字段、采样  │
├─────────────────────────────────────────┤
│  OntologyInferrer                        │
│  粗分类 + 逐表精推断 + FK匹配            │
│  LLM调用 + Pydantic输出校验              │
├─────────────────────────────────────────┤
│  OntologyImporter.import_dict()          │
│  复用现有写入逻辑                        │
└─────────────────────────────────────────┘
```

## 4. SchemaScanner

独立服务，基于SQLAlchemy inspect，不修改BaseConnector接口。只支持SQL类数据源（MySQL/PostgreSQL/SQLite）。

```python
class SchemaScanner:
    def __init__(self, connection_url: str):
        self.engine = create_engine(connection_url)

    def list_tables(self) -> list[str]:
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def scan_table(self, table_name: str) -> TableSummary:
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        row_count = self._get_row_count(table_name)
        samples = self._sample_values(table_name, columns)
        return TableSummary(name=table_name, row_count=row_count,
                           columns=columns, sample_values=samples)

    def scan_all(self) -> list[TableSummary]:
        return [self.scan_table(t) for t in self.list_tables()]

    def _get_row_count(self, table_name: str) -> int:
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM \"{table_name}\""))
            return result.scalar()

    def _sample_values(self, table_name, columns, limit=500):
        # table_name来自SQLAlchemy inspect，不是用户输入，安全
        # 用quoted_name防御性处理
        from sqlalchemy.sql import quoted_name
        safe_name = quoted_name(table_name, quote=True)
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(f"SELECT * FROM {safe_name} LIMIT :lim"), {"lim": limit}
            ).mappings().all()
        samples = {}
        for col in columns:
            col_name = col["name"]
            values = list(set(str(row[col_name]) for row in rows if row[col_name] is not None))
            samples[col_name] = values[:20]
        return samples
```

`TableSummary` 数据结构：

```python
@dataclass
class TableSummary:
    name: str
    row_count: int
    columns: list[dict]       # SQLAlchemy inspector format
    sample_values: dict[str, list[str]]  # column → top 20 distinct values
```

## 5. OntologyInferrer

### 5.1 两阶段推断

**阶段一：表级粗分类（一次LLM调用）**

输入：所有表的摘要（表名 + 字段名列表 + 行数）
输出：每张表的分类

```python
class TableClassification(BaseModel):
    name: str
    category: Literal["business", "system", "temporary", "unknown"]
    confidence: float
    description: str
```

Prompt约束：只输出JSON数组，不要其他文字。

**阶段二：逐表精推断（每张表一次LLM调用）**

输入：单张表的完整信息（字段名、类型、distinct值采样）
输出：结构化ontology定义

```python
class InferredProperty(BaseModel):
    name: str
    data_type: str
    semantic_type: str | None = None  # 从闭合词表中选择
    description: str = ""

class InferredObject(BaseModel):
    name: str                    # 中文业务名称
    source_entity: str           # 原始表名
    description: str
    business_context: str = ""
    domain: str = ""
    properties: list[InferredProperty]
    suggested_health_rules: list[dict] = []
    suggested_computed_properties: list[dict] = []
```

### 5.2 闭合语义类型词表

LLM必须从以下列表中选择semantic_type，不能自创：

```python
SEMANTIC_TYPES = [
    "text", "number", "integer", "float", "boolean",
    "date", "datetime", "timestamp",
    "currency_cny", "currency_usd",
    "percentage", "ratio",
    "phone", "email", "address", "province", "city",
    "order_status", "approval_status",
    "quantity", "weight_kg", "weight_g", "volume_l",
    "stock_code", "url", "id",
]
```

此列表与SemanticTypeFormatter已支持的类型对齐。Prompt中明确列出，要求LLM只从中选择。

### 5.3 关系推断

**代码FK匹配优先：**

```python
def infer_relationships_by_naming(objects: list[InferredObject]) -> list[dict]:
    """基于字段命名规则推断FK关系。
    规则：字段名为 {table}_id 或 {table}id → 关联到对应表的id字段。"""
    table_names = {obj.source_entity for obj in objects}
    relationships = []
    for obj in objects:
        for prop in obj.properties:
            # customer_id → t_customer.id
            if prop.name.endswith("_id"):
                ref_table = prop.name[:-3]  # 去掉 _id
                for candidate in table_names:
                    if candidate == ref_table or candidate == f"t_{ref_table}":
                        relationships.append({...})
    return relationships
```

代码匹配不上的字段，打包发给LLM做一次补充推断。

### 5.4 LLM调用与解析

```python
def _call_llm(self, prompt: str) -> dict:
    # 使用项目已配置的LLM provider (config.py)
    # 支持 Deepseek / OpenAI / Anthropic
    ...

def _parse_llm_response(self, response: str, model_class: type[BaseModel]) -> BaseModel:
    # 1. 正则提取第一个 JSON 块（{...} 或 [...]）
    # 2. json.loads 解析
    # 3. Pydantic model_validate 校验
    # 4. 校验失败 → 重试一次
    # 5. 两次都失败 → 返回None，标记为"需手动配置"
    ...
```

## 6. API端点

### 6.1 scan

```
POST /api/v1/ontology-store/{project_id}/scan
请求: { "datasource_id": "mysql_erp" }
响应: {
    "tables": [
        {
            "name": "t_order",
            "row_count": 15000,
            "columns": [{"name": "id", "type": "INTEGER"}, ...],
            "sample_values": {"status": ["pending", "shipped", ...]}
        },
        ...
    ]
}
```

纯DB操作，几秒内返回。datasource_id引用项目中已配置的数据源。

### 6.2 infer

```
POST /api/v1/ontology-store/{project_id}/infer
请求: { "datasource_id": "mysql_erp", "tables": ["t_order", "t_customer"] }
响应: {
    "objects": [InferredObject, ...],
    "relationships": [{"name": "...", "from_object": "...", ...}],
    "warnings": ["表 t_log 推断失败，需手动配置"]
}
超时: 120秒
```

### 6.3 confirm

```
POST /api/v1/ontology-store/{project_id}/confirm
请求: {
    "datasources": [{"id": "mysql_erp", "type": "sql", ...}],
    "ontology": {
        "objects": [用户确认/修改后的对象列表],
        "relationships": [用户确认/修改后的关系列表]
    }
}
响应: { "objects_created": 2, "relationships_created": 1 }
```

内部调用 `OntologyImporter.import_dict()` — 从现有 `import_yaml()` 提取的共享逻辑。

## 7. OntologyImporter重构

从现有 `import_yaml()` 提取 `import_dict()`：

```python
class OntologyImporter:
    def import_yaml(self, tenant_id, yaml_content):
        if len(yaml_content) > 1_000_000:
            raise ValueError("YAML content exceeds 1MB limit")
        config = yaml.safe_load(yaml_content)
        if not isinstance(config, dict):
            raise ValueError("YAML must be a dictionary")
        return self.import_dict(tenant_id, config)

    def import_dict(self, tenant_id, config):
        """共享逻辑：YAML导入和confirm端点都调用此方法。"""
        ontology = config.get("ontology", {})
        datasources_list = config.get("datasources", [])
        if not isinstance(datasources_list, list):
            raise ValueError("datasources must be a list")
        datasources = {ds["id"]: ds for ds in datasources_list}
        # ... 原有的遍历和写入逻辑 ...
```

## 8. 文件结构

### 新建
- `backend/app/services/schema_scanner.py` — Schema扫描服务
- `backend/app/services/ontology_inferrer.py` — AI推断服务
- `backend/app/schemas/auto_model.py` — Pydantic请求/响应模型
- `backend/tests/test_schema_scanner.py`
- `backend/tests/test_ontology_inferrer.py`
- `backend/tests/test_api_auto_model.py`
- `backend/tests/integration/test_auto_model_e2e.py`

### 修改
- `backend/app/api/ontology_store_routes.py` — 添加scan/infer/confirm端点
- `backend/app/services/ontology_importer.py` — 提取import_dict()
- `backend/app/config.py` — 添加推断相关配置（超时、重试次数）

## 9. 测试策略

- **test_schema_scanner.py** — SQLite内存数据库，创建测试表，验证扫描结果
- **test_ontology_inferrer.py** — mock LLM响应，验证：
  - 粗分类正确解析
  - 精推断输出符合Pydantic模型
  - FK代码匹配逻辑
  - LLM返回异常时的降级处理
  - 闭合语义类型词表约束
- **test_api_auto_model.py** — mock Scanner和Inferrer，验证API端点
- **test_auto_model_e2e.py** — 真实SQLite + mock LLM，全流程跑通

不测真实LLM调用。LLM交互全部mock。

## 10. 配置

```python
# config.py 新增
INFER_LLM_PROVIDER: str = "deepseek"  # 复用现有LLM配置
INFER_MAX_RETRIES: int = 1
INFER_TIMEOUT: int = 30  # 单次LLM调用超时（秒）
INFER_SAMPLE_ROWS: int = 500
INFER_DISTINCT_LIMIT: int = 20
```
