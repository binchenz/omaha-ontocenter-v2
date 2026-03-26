# Phase 2 实施计划：财务分析层

**日期：** 2026-03-26
**状态：** 进行中
**负责人：** Claude Sonnet 4.6

## 1. 目标

在 Phase 1 基础数据层的基础上，添加财务分析能力，支持深度财务分析和基本面选股。

## 2. 新增对象

### 2.1 FinancialIndicator（财务指标）

**数据源：** Tushare Pro API - `fina_indicator`

**核心字段：**
- `ts_code`: 股票代码
- `end_date`: 报告期
- `eps`: 基本每股收益
- `roe`: 净资产收益率（%）
- `roa`: 总资产报酬率（%）
- `gross_margin`: 销售毛利率（%）
- `debt_to_assets`: 资产负债率（%）
- `current_ratio`: 流动比率
- `quick_ratio`: 速动比率

**用途：**
- 盈利能力分析（ROE、ROA、毛利率）
- 偿债能力分析（资产负债率、流动比率）
- 多期财务指标对比
- 基本面选股

### 2.2 FinancialReport（财务报表）

**数据源：** Tushare Pro API - `income`, `balancesheet`, `cashflow`

**核心字段：**
- `ts_code`: 股票代码
- `end_date`: 报告期
- `ann_date`: 公告日期
- `f_ann_date`: 实际公告日期
- `report_type`: 报告类型（1-合并报表/2-单季合并）

**利润表字段（income）：**
- `total_revenue`: 营业总收入
- `revenue`: 营业收入
- `operate_profit`: 营业利润
- `total_profit`: 利润总额
- `n_income`: 净利润
- `n_income_attr_p`: 归属于母公司所有者的净利润

**资产负债表字段（balancesheet）：**
- `total_assets`: 资产总计
- `total_liab`: 负债合计
- `total_hldr_eqy_exc_min_int`: 股东权益合计（不含少数股东权益）

**现金流量表字段（cashflow）：**
- `n_cashflow_act`: 经营活动产生的现金流量净额
- `n_cashflow_inv_act`: 投资活动产生的现金流量净额
- `n_cashflow_fnc_act`: 筹资活动产生的现金流量净额

**用途：**
- 财报数据查询和分析
- 收入、利润、现金流趋势分析
- 资产负债结构分析
- 财务健康度评估

## 3. 对象关系

### 3.1 Stock -> FinancialIndicator (一对多)

```yaml
- name: stock_financial_indicators
  description: 股票的财务指标数据
  from_object: Stock
  to_object: FinancialIndicator
  type: one_to_many
  join_condition:
    from_field: ts_code
    to_field: ts_code
```

### 3.2 Stock -> FinancialReport (一对多)

```yaml
- name: stock_financial_reports
  description: 股票的财务报表数据
  from_object: Stock
  to_object: FinancialReport
  type: one_to_many
  join_condition:
    from_field: ts_code
    to_field: ts_code
```

## 4. 实施步骤

### Step 1: 更新 YAML 配置文件

**文件：** `configs/financial_stock_analysis.yaml`

**任务：**
- 添加 FinancialIndicator 对象定义
- 添加 FinancialReport 对象定义
- 添加与 Stock 的关系配置

### Step 2: 编写 FinancialIndicator 测试

**文件：** `backend/tests/test_tushare_financial_indicator.py`

**测试用例：**
1. `test_query_financial_indicator_basic()` - 基础查询测试
2. `test_query_financial_indicator_with_filters()` - 过滤条件测试
3. `test_financial_indicator_fields()` - 字段验证测试

### Step 3: 编写 FinancialReport 测试

**文件：** `backend/tests/test_tushare_financial_report.py`

**测试用例：**
1. `test_query_income_statement()` - 利润表查询测试
2. `test_query_balance_sheet()` - 资产负债表查询测试
3. `test_query_cashflow_statement()` - 现金流量表查询测试

### Step 4: 编写关系测试

**文件：** `backend/tests/test_tushare_financial_relationships.py`

**测试用例：**
1. `test_stock_with_financial_indicators()` - 股票与财务指标关联查询
2. `test_stock_with_financial_reports()` - 股票与财务报表关联查询

### Step 5: 创建集成测试

**文件：** `backend/tests/test_tushare_phase2_integration.py`

**测试场景：**
1. 完整的财务分析流程测试
2. 多期财务数据对比测试
3. 基本面选股测试

### Step 6: 运行测试验证

**命令：**
```bash
pytest backend/tests/test_tushare_financial_indicator.py -v
pytest backend/tests/test_tushare_financial_report.py -v
pytest backend/tests/test_tushare_financial_relationships.py -v
pytest backend/tests/test_tushare_phase2_integration.py -v
```

### Step 7: 更新文档

**文件：** `docs/superpowers/financial_data_objects_usage.md`

**内容：**
- 添加财务指标查询示例
- 添加财务报表查询示例
- 添加基本面分析示例

## 5. 测试策略

### 5.1 单元测试

**目标：** 验证每个对象的基本查询功能

**覆盖范围：**
- FinancialIndicator 对象的 CRUD 操作
- FinancialReport 对象的 CRUD 操作
- 字段验证和数据类型检查
- 过滤条件和排序功能

### 5.2 关系测试

**目标：** 验证对象之间的关联查询

**覆盖范围：**
- Stock -> FinancialIndicator JOIN 查询
- Stock -> FinancialReport JOIN 查询
- 多表关联查询

### 5.3 集成测试

**目标：** 验证完整的业务场景

**覆盖范围：**
- 财务指标分析场景
- 财报数据查询场景
- 基本面选股场景

## 6. 验收标准

### 6.1 功能完整性

- ✅ FinancialIndicator 对象可以正常查询
- ✅ FinancialReport 对象可以正常查询
- ✅ 支持按股票代码、报告期筛选
- ✅ 支持与 Stock 对象的关联查询

### 6.2 测试覆盖率

- ✅ 所有单元测试通过（至少 6 个测试）
- ✅ 所有关系测试通过（至少 2 个测试）
- ✅ 所有集成测试通过（至少 3 个测试）

### 6.3 文档完整性

- ✅ 使用指南包含财务分析示例
- ✅ API 文档更新
- ✅ 测试报告生成

## 7. 风险和注意事项

### 7.1 Tushare API 限制

**风险：** 财务数据查询可能受到积分限制

**应对：**
- 使用合理的查询参数（如指定报告期范围）
- 添加缓存机制
- 测试时使用少量数据

### 7.2 数据完整性

**风险：** 部分股票可能没有财务数据

**应对：**
- 在测试中使用已知有数据的股票（如平安银行 000001.SZ）
- 添加空数据处理逻辑
- 在文档中说明数据可用性

### 7.3 API 参数支持

**风险：** Tushare API 可能不支持某些字段的过滤

**应对：**
- 复用 Phase 1 的客户端过滤逻辑
- 在 `SUPPORTED_PARAMS` 中添加财务 API 的支持参数
- 测试验证过滤功能

## 8. 时间估算

| 任务 | 预计时间 |
|------|---------|
| 更新 YAML 配置 | 30 分钟 |
| 编写 FinancialIndicator 测试 | 1 小时 |
| 编写 FinancialReport 测试 | 1.5 小时 |
| 编写关系测试 | 45 分钟 |
| 创建集成测试 | 1 小时 |
| 运行测试和修复 | 1 小时 |
| 更新文档 | 45 分钟 |
| **总计** | **约 6.5 小时** |

## 9. 下一步

完成 Phase 2 后，将具备以下能力：

1. **财务指标分析**
   - 查询股票的 ROE、ROA、毛利率等指标
   - 多期财务指标对比
   - 基于财务指标的选股

2. **财务报表分析**
   - 查询利润表、资产负债表、现金流量表
   - 收入、利润、现金流趋势分析
   - 财务健康度评估

3. **基本面分析**
   - 结合股票基本信息、行情数据、财务数据
   - 全面的基本面分析能力
   - 支持价值投资策略

## 10. Phase 3 预览

Phase 3 将添加量化分析层，包括：
- TechnicalIndicator（技术指标）
- ValuationMetric（估值指标）
- Sector（板块分类）

预计工时：3-4 天
