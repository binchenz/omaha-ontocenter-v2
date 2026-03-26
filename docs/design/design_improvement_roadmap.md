# Omaha OntoCenter 设计改进建议

> 基于轻量级本体市场定位分析
> 更新时间：2026-03-17

## 一、当前设计现状

### 已实现功能 ✅

1. **轻量级本体层（阵营一能力）**
   - ✅ YAML 定义 Objects, Properties, Relationships, Metrics
   - ✅ 多数据源支持（MySQL, PostgreSQL, SQLite）
   - ✅ 自动 JOIN 查询
   - ✅ 最小识别集设计（CompetitorComparison）

2. **AI Agent 层（阵营二能力）**
   - ✅ Chat Agent 自然语言查询
   - ✅ 基于 Ontology 上下文生成 SQL
   - ✅ 自动图表生成（ECharts）

3. **API 基建层**
   - ✅ MCP Server（7个工具）
   - ✅ 数据血缘追踪
   - ✅ 资产管理

### 未实现功能 ❌

1. **语义层核心功能**
   - ❌ default_filters 自动过滤
   - ❌ computed_properties 自动展开
   - ❌ 字段语义类型验证（currency, percentage, enum）
   - ❌ 业务规则验证

2. **AI Native 核心功能**
   - ❌ AI 自动扫描数据库结构
   - ❌ 历史 SQL 查询日志学习
   - ❌ 自动推断表关系
   - ❌ 动态元数据图谱

3. **前端可视化**
   - ❌ 语义层编辑器
   - ❌ 公式构建器
   - ❌ 关系可视化

---

## 二、设计改进优先级

### P0：完成语义层基础功能（必须）

**目标：** 成为合格的"阵营一（语义层基建）"玩家

#### 1. 实现 default_filters 自动过滤

**当前问题：**
```yaml
# YAML 中定义了 default_filters，但查询时不生效
default_filters:
  - field: platform_id
    operator: "IS NOT NULL"
```

**改进方案：**
```python
# backend/app/services/query_builder.py
class SemanticQueryBuilder:
    def build_where_clause(self, object_config, user_filters):
        # 1. 读取对象的 default_filters
        default_filters = object_config.get("default_filters", [])

        # 2. 合并 default_filters 和 user_filters
        all_filters = default_filters + user_filters

        # 3. 构建 WHERE 子句
        return self._build_filter_sql(all_filters)
```

**影响：**
- CompetitorComparison 对象语义正确
- 用户无需手动添加过滤条件
- 避免查询错误数据

#### 2. 实现 computed_properties 自动展开

**当前问题：**
```yaml
# YAML 中定义了计算字段，但查询时不展开
computed_properties:
  - name: actual_price_gap
    formula: "ppy_price - mall_price"
```

**改进方案：**
```python
# backend/app/services/query_builder.py
class SemanticQueryBuilder:
    def expand_computed_property(self, property_name, object_config):
        # 1. 查找计算字段定义
        computed = self._find_computed_property(property_name, object_config)

        # 2. 展开公式中的属性名为列名
        formula = computed["formula"]
        for prop in object_config["properties"]:
            formula = formula.replace(prop["name"], prop["column"])

        # 3. 返回 SQL 表达式
        return f"({formula}) as {property_name}"
```

**影响：**
- Agent 可以直接查询计算字段
- 无需手动编写复杂 SQL 表达式
- 降低查询门槛

#### 3. 实现字段语义类型验证

**当前问题：**
```yaml
# YAML 中定义了 semantic_type，但没有验证和格式化
properties:
  - name: ppy_price
    semantic_type: currency
    currency: CNY
```

**改进方案：**
```python
# backend/app/services/semantic.py
class SemanticService:
    def format_value(self, value, semantic_type, metadata):
        if semantic_type == "currency":
            currency = metadata.get("currency", "CNY")
            return f"{currency} {value:,.2f}"
        elif semantic_type == "percentage":
            return f"{value * 100:.2f}%"
        elif semantic_type == "enum":
            enum_values = metadata.get("enum_values", [])
            return self._get_enum_label(value, enum_values)
        return value
```

**影响：**
- 查询结果自动格式化
- 提升用户体验
- 支持国际化

---

### P1：增强 AI Native 能力（重要）

**目标：** 成为合格的"阵营二（AI Native）"玩家

#### 1. AI 自动扫描数据库结构

**设计方案：**
```python
# backend/app/services/metadata_scanner.py
class MetadataScanner:
    def scan_database(self, datasource_config):
        """扫描数据库结构，生成元数据"""
        # 1. 连接数据库
        conn = self._connect(datasource_config)

        # 2. 扫描所有表
        tables = self._get_all_tables(conn)

        # 3. 扫描每个表的列
        metadata = {}
        for table in tables:
            columns = self._get_table_columns(conn, table)
            metadata[table] = {
                "columns": columns,
                "primary_key": self._infer_primary_key(columns),
                "foreign_keys": self._infer_foreign_keys(conn, table)
            }

        return metadata
```

**影响：**
- 自动发现数据库中的表和字段
- 减少手动配置工作
- 类似 Secoda 的能力

#### 2. 分析历史 SQL 查询日志

**设计方案：**
```python
# backend/app/services/query_analyzer.py
class QueryAnalyzer:
    def analyze_query_logs(self, logs):
        """分析历史 SQL 查询，推断表关系和常用模式"""
        # 1. 解析 SQL 语句
        parsed_queries = [self._parse_sql(log) for log in logs]

        # 2. 提取 JOIN 模式
        join_patterns = self._extract_join_patterns(parsed_queries)

        # 3. 提取常用字段组合
        field_combinations = self._extract_field_combinations(parsed_queries)

        # 4. 推断表关系
        relationships = self._infer_relationships(join_patterns)

        return {
            "join_patterns": join_patterns,
            "field_combinations": field_combinations,
            "relationships": relationships
        }
```

**影响：**
- 自动推断表之间的关系
- 学习用户的查询习惯
- 类似 Secoda 的能力

#### 3. 动态元数据图谱

**设计方案：**
```python
# backend/app/services/metadata_graph.py
class MetadataGraph:
    def __init__(self):
        self.graph = nx.DiGraph()  # 使用 NetworkX 构建图

    def build_from_ontology(self, ontology_config):
        """从 Ontology 配置构建图"""
        # 1. 添加对象节点
        for obj in ontology_config["objects"]:
            self.graph.add_node(obj["name"], type="object", **obj)

        # 2. 添加关系边
        for rel in ontology_config["relationships"]:
            self.graph.add_edge(
                rel["from_object"],
                rel["to_object"],
                type=rel["type"],
                **rel
            )

    def enrich_from_scanner(self, metadata):
        """从扫描结果丰富图"""
        # 添加自动发现的表和关系
        pass

    def enrich_from_analyzer(self, analysis):
        """从查询分析丰富图"""
        # 添加推断的关系和模式
        pass

    def get_context_for_query(self, query_intent):
        """为查询意图获取相关上下文"""
        # 基于图结构返回相关的对象、字段、关系
        pass
```

**影响：**
- 统一管理元数据
- 支持 Agent 智能查询
- 随着使用不断学习和优化

#### 4. 上下文对齐增强

**设计方案：**
```python
# backend/app/services/context_aligner.py
class ContextAligner:
    def __init__(self):
        self.business_terms = {}  # 业务术语字典

    def load_from_ontology(self, ontology_config):
        """从 Ontology 的 business_context 加载业务术语"""
        for obj in ontology_config["objects"]:
            for prop in obj["properties"]:
                if "business_context" in prop:
                    self.business_terms[prop["name"]] = {
                        "definition": prop["business_context"],
                        "object": obj["name"],
                        "column": prop["column"]
                    }

    def learn_from_queries(self, query, result, feedback):
        """从用户查询和反馈中学习业务术语"""
        # 使用 LLM 提取查询中的业务术语
        # 记录用户的反馈（是否满意）
        # 更新业务术语字典
        pass

    def resolve_term(self, term):
        """解析业务术语到数据库字段"""
        if term in self.business_terms:
            return self.business_terms[term]

        # 使用 LLM 推断
        return self._infer_term_meaning(term)
```

**影响：**
- 解决"大客户"、"活跃用户"等企业特定术语
- 类似 Dot 的"内部数据方言"学习
- 提升 Agent 查询准确性

---

### P2：前端可视化编辑器（重要）

**目标：** 降低配置门槛，提升用户体验

#### 1. 三栏式语义层编辑器

**设计方案：**
```
┌─────────────────────────────────────────────────────────┐
│  对象列表    │    字段编辑区             │  预览/测试    │
│  📦 Product  │  ┌─ 基础字段 ──────────┐ │  SQL预览      │
│  📦 Category │  │ price    [货币▼]    │ │  Agent上下文  │
│              │  │ ✓ 必填  ✓ 唯一      │ │  示例数据     │
│              │  └────────────────────┘ │               │
│              │  ┌─ 计算字段 ──────────┐ │               │
│              │  │ gross_margin  [fx] │ │               │
│              │  │ (price - cost) / price │           │
│              │  └────────────────────┘ │               │
│              │  ┌─ 关系 ──────────────┐ │               │
│              │  │ → Category (多对一) │ │               │
│              │  └────────────────────┘ │               │
└─────────────────────────────────────────────────────────┘
```

**影响：**
- 数据工程师无需手动编写 YAML
- 可视化编辑，降低出错率
- 实时预览，提升开发效率

#### 2. 公式构建器

**设计方案：**
```
公式构建器:
┌─────────────────────────────────────────────┐
│  ( [price ▼] - [cost ▼] ) / [price ▼]      │
│                                             │
│  可用字段: price  cost  sales_count  ...    │
│  运算符:   + - * /  >  <  AND  OR  IF       │
│  函数:     SUM  AVG  COUNT  MAX  MIN        │
│                                             │
│  预览结果: 0.35 (35%)                       │
└─────────────────────────────────────────────┘
```

**影响：**
- 业务分析师可以自己定义计算字段
- 避免 SQL 语法错误
- 支持复杂的业务逻辑

---

### P3：数据写回和 Pipeline（可选）

**目标：** 缩小与 Palantir 的差距

#### 1. 数据写回能力

**设计方案：**
```python
# backend/app/services/data_writer.py
class DataWriter:
    def update_data(self, object_type, filters, updates):
        """更新数据"""
        # 1. 权限检查
        if not self._check_permission(object_type, "write"):
            raise PermissionError()

        # 2. 构建 UPDATE 语句
        sql = self._build_update_sql(object_type, filters, updates)

        # 3. 执行更新
        result = self._execute(sql)

        # 4. 记录审计日志
        self._log_audit(object_type, "update", filters, updates)

        return result
```

**影响：**
- 支持数据修改
- 需要完善的权限系统
- 需要审计日志

#### 2. Pipeline/Transform 系统

**设计方案：**
```yaml
# pipeline.yaml
pipelines:
  - name: daily_price_sync
    schedule: "0 2 * * *"  # 每天凌晨2点
    steps:
      - name: extract
        type: query
        object: PriceComparison
        filters:
          - field: p_date
            operator: "="
            value: "{{ yesterday }}"

      - name: transform
        type: python
        script: |
          def transform(data):
              # 计算价格优势率
              return calculate_advantage_rate(data)

      - name: load
        type: write
        object: DailyMetrics
        mode: append
```

**影响：**
- 支持数据转换流程
- 支持定时调度
- 类似 dbt 的能力

---

## 三、实施路线图

### Phase 4.1：语义层基础功能（2周）

**Week 1：**
- [ ] 实现 default_filters 自动过滤
- [ ] 实现 computed_properties 自动展开
- [ ] 修复 CompetitorComparison 测试失败

**Week 2：**
- [ ] 实现字段语义类型验证
- [ ] 实现业务规则验证
- [ ] 完善测试覆盖率

**交付物：**
- ✅ default_filters 功能完整
- ✅ computed_properties 功能完整
- ✅ 所有测试通过

---

### Phase 4.2：AI Native 能力（4周）

**Week 1-2：元数据扫描**
- [ ] 实现 MetadataScanner
- [ ] 支持 MySQL, PostgreSQL, SQLite
- [ ] 自动推断主键和外键

**Week 3：查询分析**
- [ ] 实现 QueryAnalyzer
- [ ] 分析历史 SQL 日志
- [ ] 提取 JOIN 模式

**Week 4：元数据图谱**
- [ ] 实现 MetadataGraph
- [ ] 集成 NetworkX
- [ ] 为 Agent 提供上下文

**交付物：**
- ✅ 自动扫描数据库结构
- ✅ 自动推断表关系
- ✅ 动态元数据图谱

---

### Phase 4.3：前端编辑器（3周）

**Week 1：基础框架**
- [ ] 三栏式布局
- [ ] 对象列表组件
- [ ] 字段编辑组件

**Week 2：公式构建器**
- [ ] 可视化公式编辑
- [ ] 实时预览
- [ ] 语法验证

**Week 3：关系可视化**
- [ ] 关系图组件
- [ ] 拖拽编辑
- [ ] 自动布局

**交付物：**
- ✅ 可视化语义层编辑器
- ✅ 公式构建器
- ✅ 关系可视化

---

### Phase 5：数据写回和 Pipeline（6周）

**Week 1-2：权限系统**
- [ ] RBAC 权限模型
- [ ] 对象级权限
- [ ] 字段级权限

**Week 3-4：数据写回**
- [ ] UPDATE 支持
- [ ] INSERT 支持
- [ ] DELETE 支持
- [ ] 审计日志

**Week 5-6：Pipeline 系统**
- [ ] Pipeline 定义（YAML）
- [ ] 调度引擎
- [ ] 监控和告警

**交付物：**
- ✅ 完整的权限系统
- ✅ 数据写回能力
- ✅ Pipeline/Transform 系统

---

## 四、关键设计决策

### 1. 轻量级 vs 重型

**决策：** 保持轻量级，不重构底层数仓

**理由：**
- 符合市场定位（轻量级本体）
- 降低部署成本
- 快速迭代

### 2. YAML vs GUI

**决策：** YAML 为主，GUI 为辅

**理由：**
- YAML 易于版本控制
- YAML 易于协作
- GUI 降低配置门槛（Phase 4.3）

### 3. 手动配置 vs AI 自动化

**决策：** 两者结合，逐步演进

**理由：**
- 手动配置保证可控性（Phase 4.1）
- AI 自动化提升效率（Phase 4.2）
- 符合市场趋势（从阵营一到阵营二）

### 4. 自研 vs 集成

**决策：** 核心功能自研，周边功能集成

**理由：**
- 语义层、Agent 是核心竞争力，必须自研
- 可视化、调度等可以集成开源方案
- 降低开发成本

---

## 五、与竞品的差异化

### vs dbt Semantic Layer

| 维度 | dbt | Omaha OntoCenter |
|------|-----|------------------|
| 定义方式 | YAML | ✅ YAML + GUI |
| 查询方式 | SQL/API | ✅ Chat Agent |
| AI 能力 | 无 | ✅ 自动扫描 + 学习 |

### vs Secoda

| 维度 | Secoda | Omaha OntoCenter |
|------|--------|------------------|
| 元数据管理 | AI 自动化 | ✅ AI 自动化 |
| 语义层定义 | 无 | ✅ YAML 定义 |
| 查询能力 | 搜索 | ✅ Chat Agent |

### vs Kyligence

| 维度 | Kyligence | Omaha OntoCenter |
|------|-----------|------------------|
| 底层引擎 | 重型 OLAP | ✅ 轻量级 |
| 部署成本 | 高 | ✅ 低 |
| AI 能力 | 有限 | ✅ Chat Agent + 自动化 |

---

## 六、总结

基于市场定位分析，Omaha OntoCenter 的设计改进方向应该是：

1. **P0：完成语义层基础功能**
   - 成为合格的"阵营一（语义层基建）"玩家
   - 实现 default_filters 和 computed_properties

2. **P1：增强 AI Native 能力**
   - 成为合格的"阵营二（AI Native）"玩家
   - 实现自动扫描、查询分析、元数据图谱

3. **P2：前端可视化编辑器**
   - 降低配置门槛
   - 提升用户体验

4. **P3：数据写回和 Pipeline**
   - 缩小与 Palantir 的差距
   - 但不是当前阶段的重点

通过这样的设计改进，Omaha OntoCenter 将成为一个**真正融合"阵营一 + 阵营二 + 阵营三"能力的轻量级本体平台**，在市场上形成清晰的差异化优势。
