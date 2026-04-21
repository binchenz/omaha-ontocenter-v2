# Omaha OntoCenter — Phase 1: 通用 Connector 框架设计

## 背景与愿景

Omaha OntoCenter 的长期目标是成为中国中小企业的 Palantir — 一个通用数据整合 + AI 决策平台，支持私有化部署。

当前产品聚焦金融（A 股分析），数据源硬编码在 OmahaService 中（Tushare/PostgreSQL/MySQL/SQLite）。短期需要扩展到零售供应链、制造业、短剧创作等行业，每个行业有不同的数据源类型。

Phase 1 的目标：**建立插件化 Connector 框架**，让新增数据源类型不需要修改核心查询逻辑。

## 产品定位

- **路径：** 先 Foundry（数据底座）后 AIP（AI 层）
- **部署：** 私有化为主 + 可选托管
- **用户分层：** 技术人员做配置接入，业务人员用 Explorer/AI 助手做分析
- **AI 接入：** 后续通过 MCP 工具让 Claude Code 辅助数据接入配置（本 Phase 不实现，但架构需预留）

## 架构设计

### Connector 插件体系

```
backend/app/connectors/
├── base.py              # BaseConnector 抽象类
├── registry.py          # type → Connector class 映射
├── sql_connector.py     # PostgreSQL / MySQL / SQLite
├── tushare_connector.py # Tushare Pro API
├── csv_connector.py     # CSV / Excel 文件上传 → 导入数据库
├── rest_connector.py    # 通用 REST API
└── __init__.py
```

### BaseConnector 接口

```python
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass

@dataclass
class ColumnDef:
    name: str
    type: str  # string, integer, decimal, date, datetime, boolean
    nullable: bool = True
    description: str = ""

class BaseConnector(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def test_connection(self) -> bool:
        """验证连接是否可用"""

    @abstractmethod
    def discover_schema(self, source: str) -> list[ColumnDef]:
        """自动发现数据源的 Schema（表结构或 API 字段）"""

    @abstractmethod
    def query(
        self,
        source: str,
        columns: list[str] | None = None,
        filters: list[dict] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """执行查询，返回行列表"""

    def close(self) -> None:
        """释放连接资源（可选覆盖）"""
```

### Connector 注册表

```python
# registry.py
_CONNECTORS: dict[str, type[BaseConnector]] = {}

def register(type_name: str, cls: type[BaseConnector]):
    _CONNECTORS[type_name] = cls

def get_connector(type_name: str, config: dict) -> BaseConnector:
    cls = _CONNECTORS.get(type_name)
    if not cls:
        raise ValueError(f"Unknown datasource type: {type_name}")
    return cls(config)
```

各 Connector 在 `__init__.py` 中自注册：

```python
from .registry import register
from .sql_connector import SQLConnector
from .tushare_connector import TushareConnector
from .csv_connector import CSVConnector
from .rest_connector import RESTConnector

register("postgresql", SQLConnector)
register("mysql", SQLConnector)
register("sqlite", SQLConnector)
register("tushare", TushareConnector)
register("csv", CSVConnector)
register("excel", CSVConnector)
register("rest_api", RESTConnector)
```

### OmahaService 重构

当前 `omaha.py` 中的数据源处理逻辑（约 200 行）提取到对应 Connector 中。`query_objects()` 简化为：

```python
def query_objects(self, config_yaml, object_type, ...):
    ontology = self.build_ontology(config_yaml)
    obj_def = ontology["objects"][object_type]
    ds_config = ontology["datasources"][obj_def["datasource"]]

    connector = registry.get_connector(ds_config["type"], ds_config["connection"])
    try:
        rows = connector.query(
            source=obj_def["table"] or obj_def["api_name"],
            columns=selected_columns,
            filters=filters,
            limit=limit,
        )
        return {"success": True, "data": rows}
    finally:
        connector.close()
```

## 首批 Connector 详细设计

### 1. SQLConnector（重构现有逻辑）

- 统一处理 PostgreSQL、MySQL、SQLite
- 使用 SQLAlchemy 创建临时 engine（不复用应用主 engine）
- `discover_schema` 通过 `inspect(engine).get_columns(table)` 实现
- `query` 构建 SQL 并执行，复用现有的 filter → WHERE 转换逻辑

### 2. TushareConnector（重构现有逻辑）

- 提取 `omaha.py` 中的 Tushare 调用逻辑
- `discover_schema` 返回 Tushare API 的已知字段定义（从 YAML 配置中读取）
- `query` 调用 `tushare.pro_api` 并转换为统一格式
- `test_connection` 调用 `stock_basic` 验证 token 有效性

### 3. CSVConnector（新增）

接入流程：
1. 用户上传 CSV/Excel 文件到 `/api/v1/datasources/{project_id}/upload`
2. 后端解析文件，推断列类型（pandas `read_csv`/`read_excel` + `dtypes`）
3. 数据导入到项目专属 SQLite 数据库（`data/{project_id}/imported.db`）
4. 后续查询走 SQLConnector（对上层透明）

```python
class CSVConnector(BaseConnector):
    def ingest(self, file_path: str, table_name: str) -> list[ColumnDef]:
        """解析文件并导入到项目数据库，返回推断的 Schema"""
        df = pd.read_csv(file_path)  # 或 read_excel
        engine = create_engine(f"sqlite:///data/{project_id}/imported.db")
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        return self._infer_schema(df)

    def query(self, source, columns, filters, limit):
        # 委托给 SQLConnector 查询已导入的数据
        sql_conn = SQLConnector({"database": f"data/{project_id}/imported.db"})
        return sql_conn.query(source, columns, filters, limit)
```

文件存储：
- 原始文件保存在 `data/{project_id}/uploads/` 目录
- 导入后的数据在 `data/{project_id}/imported.db`
- 私有化部署时这些目录在客户服务器本地

### 4. RESTConnector（新增）

支持通用 REST API 接入：

```yaml
datasources:
  - id: erp_api
    type: rest_api
    connection:
      base_url: https://erp.company.com/api/v1
      auth_type: bearer  # bearer / basic / api_key / none
      token: ${ERP_TOKEN}
      # 或 api_key_header: X-API-Key
      # 或 username/password for basic auth
```

```python
class RESTConnector(BaseConnector):
    def query(self, source, columns, filters, limit):
        url = f"{self.config['base_url']}/{source}"
        params = self._build_params(filters, limit)
        headers = self._build_auth_headers()
        response = httpx.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        # 支持常见的 JSON 响应格式：
        # {"data": [...]} 或 {"items": [...]} 或 直接 [...]
        rows = self._extract_rows(data)
        return self._select_columns(rows, columns)
```

YAML 中需要配置响应数据的路径：

```yaml
ontology:
  objects:
    - name: Order
      datasource: erp_api
      api_name: orders          # REST 路径
      response_path: data.items # JSON 响应中数据数组的路径
      properties:
        - name: order_id
          column: id
          type: string
```

## 新增 API 端点

```
POST   /api/v1/datasources/{project_id}/test       # 测试数据源连接
POST   /api/v1/datasources/{project_id}/discover    # 发现 Schema
POST   /api/v1/datasources/{project_id}/upload      # 上传 CSV/Excel
GET    /api/v1/datasources/{project_id}/list        # 列出已配置的数据源
```

## 前端变化

### Settings 页面新增「数据源」Tab

```
设置
├── 项目管理（已有）
├── 数据源          ← 新增
├── 配置编辑（已有）
└── API Keys（已有）
```

数据源 Tab 内容：
- 数据源列表卡片（名称、类型、状态指示灯）
- 每个数据源有「测试连接」按钮
- CSV/Excel 上传区域（拖拽或点击上传）
- 上传后显示推断的 Schema，用户确认后导入

### Explorer 页面

无需修改 — Connector 框架对查询层透明。用户选择对象类型后，底层自动路由到正确的 Connector。

## YAML 配置兼容性

现有的 `financial_stock_analysis.yaml` 完全兼容，无需修改：
- `type: tushare` → TushareConnector
- `type: postgresql` / `type: mysql` / `type: sqlite` → SQLConnector

新增类型：
- `type: csv` / `type: excel` → CSVConnector
- `type: rest_api` → RESTConnector

## MCP 工具扩展（预留）

本 Phase 不实现 AI 驱动接入，但 Connector 框架的 `test_connection`、`discover_schema` 方法天然可以暴露为 MCP 工具，为后续 Claude Code 辅助接入做准备：

```python
# 未来 MCP 工具（本 Phase 不实现）
# test_datasource_connection(type, config) → bool
# discover_datasource_schema(type, config, source) → list[ColumnDef]
# generate_ontology_yaml(schema, object_name) → str
```

## 测试策略

- 单元测试：每个 Connector 的 `query`、`discover_schema`、`test_connection`
- 集成测试：CSV 上传 → 导入 → 查询完整流程
- 现有测试：确保 Tushare 和 SQL 相关测试在重构后仍然通过
- 前端：Settings 数据源 Tab 的交互测试

## 不在范围内

- 数据 Pipeline / ETL / 定时同步（Phase 3）
- AI 驱动的自动建模（后续 Phase）
- MongoDB / Elasticsearch 等 NoSQL Connector（Phase 2）
- 多租户隔离和 RBAC（穿插在后续 Phase）
- 可视化本体编辑器（Phase 2）
