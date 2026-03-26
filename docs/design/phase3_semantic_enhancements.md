# Phase 3: 语义层增强设计方案

**创建日期**: 2026-03-26
**状态**: 设计中
**预计工期**: 7 工作日
**负责人**: Claude + 用户

---

## 1. 背景与目标

### 1.1 当前状态

**已完成功能（Phase 1 & 2）：**
- ✅ 基础数据层：Stock、DailyQuote、Industry
- ✅ 财务分析层：FinancialIndicator、IncomeStatement
- ✅ 基本查询功能：过滤、排序、分页、关联查询
- ✅ 客户端过滤增强：支持比较操作符

**存在的问题：**
1. **数据展示不友好**
   - 百分比显示为小数：`0.1089` 而非 `10.89%`
   - 金额无单位：`123456789` 而非 `¥1.23亿`
   - 日期格式不统一：`20231231` 而非 `2023-12-31`

2. **计算字段配置复杂**
   - 用户需要手动展开复杂公式
   - 嵌套计算字段难以维护

3. **缺少语义验证**
   - 无法验证字段类型是否正确
   - 计算字段依赖关系不清晰

### 1.2 Phase 3 目标

**核心目标：** 增强语义层，提供更友好的数据展示和更强大的计算能力

**具体目标：**
1. ✅ 实现 `semantic_type` 系统，自动格式化数据展示
2. ✅ 实现 `computed_properties`，支持嵌套计算字段
3. ✅ 添加语义类型验证，确保配置正确性
4. ✅ 提供完整的测试覆盖

---

## 2. 核心概念

### 2.1 Semantic Type（语义类型）

**定义：** 描述字段的业务含义和展示格式的元数据

**支持的类型：**

| 类型 | 说明 | 示例输入 | 示例输出 |
|------|------|----------|----------|
| `percentage` | 百分比 | `0.1089` | `10.89%` |
| `currency_cny` | 人民币金额 | `123456789` | `¥1.23亿` |
| `date` | 日期 | `20231231` | `2023-12-31` |
| `stock_code` | 股票代码 | `000001.SZ` | `000001.SZ` |
| `text` | 普通文本 | `平安银行` | `平安银行` |
| `number` | 数值 | `123.45` | `123.45` |

**配置示例：**
```yaml
properties:
  - name: roe
    type: float
    semantic_type: percentage  # 自动格式化为百分比

  - name: total_revenue
    type: float
    semantic_type: currency_cny  # 自动格式化为人民币
```

### 2.2 Computed Properties（计算属性）

**定义：** 基于其他字段动态计算的虚拟字段

**支持的表达式：**
- 算术运算：`+`, `-`, `*`, `/`
- 字段引用：`{field_name}`
- 嵌套引用：`{computed_field_name}`

**配置示例：**
```yaml
computed_properties:
  # 简单计算
  - name: revenue_growth_rate
    expression: "({total_revenue} - {prev_revenue}) / {prev_revenue}"
    semantic_type: percentage
    description: "营业收入增长率"

  # 嵌套计算
  - name: profit_margin
    expression: "{net_profit} / {total_revenue}"
    semantic_type: percentage

  - name: adjusted_profit_margin
    expression: "{profit_margin} * 1.1"  # 引用计算字段
    semantic_type: percentage
```

**执行顺序：**
系统会自动分析依赖关系，按拓扑排序执行计算：
1. 先计算无依赖的字段
2. 再计算依赖已计算字段的字段
3. 检测循环依赖并报错

---

## 3. 技术方案

### 3.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│  /api/v1/semantic_query (接收查询请求)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              SemanticQueryBuilder                        │
│  - 解析查询请求                                          │
│  - 构建数据源查询                                        │
│  - 应用过滤器                                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           ComputedPropertyEngine                         │
│  - 解析计算表达式                                        │
│  - 分析依赖关系（拓扑排序）                              │
│  - 执行计算                                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            SemanticTypeFormatter                         │
│  - 根据 semantic_type 格式化数据                         │
│  - percentage → "10.89%"                                 │
│  - currency_cny → "¥1.23亿"                              │
│  - date → "2023-12-31"                                   │
└─────────────────────────────────────────────────────────┘
```

### 3.2 核心模块设计

#### 3.2.1 SemanticTypeFormatter

**职责：** 根据 semantic_type 格式化数据

**实现位置：** `backend/app/services/semantic_formatter.py`

**核心方法：**
```python
class SemanticTypeFormatter:
    @staticmethod
    def format_value(value: Any, semantic_type: str) -> str:
        """根据语义类型格式化值"""
        if semantic_type == "percentage":
            return f"{value * 100:.2f}%"
        elif semantic_type == "currency_cny":
            return format_currency_cny(value)
        elif semantic_type == "date":
            return format_date(value)
        # ... 其他类型
        return str(value)
```

#### 3.2.2 ComputedPropertyEngine

**职责：** 解析和执行计算属性

**实现位置：** `backend/app/services/computed_property_engine.py`

**核心方法：**
```python
class ComputedPropertyEngine:
    def compute_properties(self, df: pd.DataFrame,
                          computed_props: List[Dict]) -> pd.DataFrame:
        """计算所有计算属性"""
        # 1. 构建依赖图
        dep_graph = self._build_dependency_graph(computed_props)

        # 2. 拓扑排序
        sorted_props = self._topological_sort(dep_graph)

        # 3. 按顺序执行计算
        for prop in sorted_props:
            df[prop['name']] = self._evaluate_expression(
                df, prop['expression']
            )

        return df
```

#### 3.2.3 SemanticTypeValidator

**职责：** 验证语义类型配置的正确性

**实现位置：** `backend/app/services/semantic_validator.py`

**验证规则：**
1. `semantic_type` 必须是支持的类型之一
2. 计算属性的依赖字段必须存在
3. 不能存在循环依赖
4. 表达式语法必须正确

---

## 4. 实施计划

### 4.1 任务分解

**Task 1: 实现 SemanticTypeFormatter（1 天）**
- [ ] 创建 `semantic_formatter.py`
- [ ] 实现 percentage 格式化
- [ ] 实现 currency_cny 格式化
- [ ] 实现 date 格式化
- [ ] 编写单元测试

**Task 2: 实现 ComputedPropertyEngine（2 天）**
- [ ] 创建 `computed_property_engine.py`
- [ ] 实现表达式解析
- [ ] 实现依赖图构建
- [ ] 实现拓扑排序
- [ ] 实现表达式求值
- [ ] 编写单元测试

**Task 3: 实现 SemanticTypeValidator（1 天）**
- [ ] 创建 `semantic_validator.py`
- [ ] 实现类型验证
- [ ] 实现依赖验证
- [ ] 实现循环依赖检测
- [ ] 编写单元测试

**Task 4: 集成到 SemanticQueryBuilder（1 天）**
- [ ] 修改 `omaha.py`
- [ ] 集成 ComputedPropertyEngine
- [ ] 集成 SemanticTypeFormatter
- [ ] 添加配置加载逻辑

**Task 5: 编写集成测试（1 天）**
- [ ] 测试完整查询流程
- [ ] 测试嵌套计算字段
- [ ] 测试格式化输出
- [ ] 测试错误处理

**Task 6: 更新配置文件（1 天）**
- [ ] 为 FinancialIndicator 添加 semantic_type
- [ ] 为 IncomeStatement 添加 semantic_type
- [ ] 添加 computed_properties 示例
- [ ] 更新文档

---

## 5. 测试策略

### 5.1 单元测试

**test_semantic_formatter.py**
```python
def test_format_percentage():
    assert format_value(0.1089, "percentage") == "10.89%"

def test_format_currency_cny():
    assert format_value(123456789, "currency_cny") == "¥1.23亿"

def test_format_date():
    assert format_value("20231231", "date") == "2023-12-31"
```

**test_computed_property_engine.py**
```python
def test_simple_computation():
    # 测试简单计算

def test_nested_computation():
    # 测试嵌套计算

def test_circular_dependency_detection():
    # 测试循环依赖检测
```

### 5.2 集成测试

**test_semantic_query_integration.py**
```python
def test_query_with_semantic_types():
    # 测试带语义类型的查询

def test_query_with_computed_properties():
    # 测试带计算属性的查询

def test_query_with_both():
    # 测试同时使用语义类型和计算属性
```

---

## 6. 配置示例

### 6.1 FinancialIndicator 配置增强

```yaml
objects:
  - name: FinancialIndicator
    datasource: tushare_pro
    api_name: fina_indicator
    properties:
      - name: ts_code
        type: string
        semantic_type: stock_code

      - name: end_date
        type: string
        semantic_type: date

      - name: eps
        type: float
        semantic_type: number
        description: "每股收益"

      - name: roe
        type: float
        semantic_type: percentage
        description: "净资产收益率"

      - name: roa
        type: float
        semantic_type: percentage
        description: "总资产收益率"

      - name: gross_profit_margin
        type: float
        semantic_type: percentage
        description: "销售毛利率"

      - name: debt_to_assets
        type: float
        semantic_type: percentage
        description: "资产负债率"

    computed_properties:
      - name: roe_level
        expression: "CASE WHEN {roe} > 0.15 THEN '优秀' WHEN {roe} > 0.10 THEN '良好' ELSE '一般' END"
        semantic_type: text
        description: "ROE 评级"

      - name: financial_health_score
        expression: "{roe} * 0.4 + {roa} * 0.3 + {gross_profit_margin} * 0.3"
        semantic_type: percentage
        description: "财务健康度评分"
```

---

## 7. 风险与挑战

### 7.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 表达式解析复杂度高 | 开发时间延长 | 使用成熟的表达式解析库（如 `simpleeval`） |
| 循环依赖检测遗漏 | 运行时错误 | 完善的单元测试 + 拓扑排序算法 |
| 性能问题（大数据集） | 查询响应慢 | 优化计算逻辑 + 缓存机制 |

### 7.2 兼容性风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 破坏现有 API | 客户端报错 | 保持向后兼容，新功能可选 |
| 配置文件格式变更 | 配置失效 | 提供配置迁移脚本 |

---

## 8. 成功标准

### 8.1 功能完整性
- ✅ 支持 6 种 semantic_type
- ✅ 支持嵌套 computed_properties
- ✅ 支持循环依赖检测
- ✅ 提供完整的错误提示

### 8.2 测试覆盖率
- ✅ 单元测试覆盖率 > 90%
- ✅ 集成测试覆盖核心场景
- ✅ 所有测试通过

### 8.3 性能指标
- ✅ 查询响应时间 < 2 秒（1000 条数据）
- ✅ 计算属性执行时间 < 500ms

---

## 9. 后续优化方向

### 9.1 短期优化（Phase 3.1）
- 支持更多 semantic_type（如 `currency_usd`、`datetime`）
- 支持更复杂的表达式（如条件表达式、聚合函数）
- 添加计算结果缓存

### 9.2 长期优化（Phase 4+）
- 支持自定义格式化函数
- 支持跨对象计算属性
- 提供可视化配置界面

---

## 10. 参考资料

- [Tushare Pro API 文档](https://tushare.pro/document/2)
- [Pandas DataFrame 计算最佳实践](https://pandas.pydata.org/docs/)
- [拓扑排序算法](https://en.wikipedia.org/wiki/Topological_sorting)

---

**文档版本**: v1.0
**最后更新**: 2026-03-26

