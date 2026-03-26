# 金融数据对象使用指南

## 概述

Omaha OntoCenter 现已支持基于 Tushare Pro 的金融数据查询功能，提供股票基本信息、日线行情和行业分类数据。

## 配置文件

配置文件位置：`/configs/financial_stock_analysis.yaml`

## 可用对象

### 1. Stock（股票基本信息）

**描述：** 查询 A 股市场上市公司的基本信息。

**数据源：** Tushare Pro API (`stock_basic`)

**主要字段：**
- `ts_code`: 股票代码（如 000001.SZ）
- `name`: 股票名称（如 平安银行）
- `industry`: 所属行业
- `area`: 地域
- `market`: 市场类型
- `list_date`: 上市日期

**默认过滤：** 只返回上市状态的股票（`list_status='L'`）

**查询示例：**

```python
# 查询所有银行股
service.query_objects(
    config_yaml=config_yaml,
    object_type="Stock",
    selected_columns=["ts_code", "name", "industry"],
    filters=[{"field": "industry", "value": "银行"}],
    limit=10
)
```

### 2. DailyQuote（日线行情）

**描述：** 查询股票的日线行情数据。

**数据源：** Tushare Pro API (`daily`)

**主要字段：**
- `ts_code`: 股票代码
- `trade_date`: 交易日期（YYYYMMDD）
- `open`, `high`, `low`, `close`: OHLC 数据
- `pct_chg`: 涨跌幅（%）
- `vol`: 成交量（手）
- `amount`: 成交额（千元）

**查询示例：**

```python
# 查询平安银行最近 10 天的行情
service.query_objects(
    config_yaml=config_yaml,
    object_type="DailyQuote",
    selected_columns=["trade_date", "close", "pct_chg"],
    filters=[{"field": "ts_code", "value": "000001.SZ"}],
    limit=10
)
```

### 3. Industry（行业分类）

**描述：** 查询行业分类信息。

**数据源：** Tushare Pro API (`stock_basic` 聚合)

**主要字段：**
- `industry`: 行业名称

**查询示例：**

```python
# 查询所有行业
service.query_objects(
    config_yaml=config_yaml,
    object_type="Industry",
    selected_columns=["industry"],
    filters=[],
    limit=50
)
```

## 关系

### Stock -> DailyQuote（一对多）

一只股票有多条日线行情记录。

**关系名称：** `stock_daily_quotes`

**使用方法：** 先查询 Stock，再用 `ts_code` 查询 DailyQuote。

### Stock -> Industry（多对一）

多只股票属于同一个行业。

**关系名称：** `stock_industry`

**使用方法：** 先查询 Industry，再用 `industry` 字段查询 Stock。

## 环境变量

需要设置 Tushare Pro API Token：

```bash
export TUSHARE_TOKEN=your_token_here
```

## 测试

运行所有金融数据对象测试：

```bash
cd backend
pytest tests/test_tushare_*.py -v
```

## 常见场景

### 场景 1：查找某个行业的所有股票

```python
# 1. 查询行业
industry_result = service.query_objects(
    config_yaml=config_yaml,
    object_type="Industry",
    selected_columns=["industry"],
    filters=[{"field": "industry", "value": "银行"}],
    limit=1
)

# 2. 查询该行业的股票
stock_result = service.query_objects(
    config_yaml=config_yaml,
    object_type="Stock",
    selected_columns=["ts_code", "name"],
    filters=[{"field": "industry", "value": "银行"}],
    limit=100
)
```

### 场景 2：分析某只股票的价格走势

```python
# 1. 查询股票信息
stock = service.query_objects(
    config_yaml=config_yaml,
    object_type="Stock",
    selected_columns=["ts_code", "name"],
    filters=[{"field": "ts_code", "value": "000001.SZ"}],
    limit=1
)

# 2. 查询历史行情
quotes = service.query_objects(
    config_yaml=config_yaml,
    object_type="DailyQuote",
    selected_columns=["trade_date", "close", "pct_chg"],
    filters=[{"field": "ts_code", "value": "000001.SZ"}],
    limit=30
)
```

## 限制

1. **Tushare API 限制：** 免费账户有积分限制，请合理控制查询频率
2. **不支持 JOIN：** Tushare 数据源不支持 SQL JOIN，需要分步查询
3. **数据延迟：** 行情数据可能有延迟，具体取决于 Tushare Pro 账户等级

## 下一步

Phase 2 将添加：
- FinancialIndicator（财务指标）
- FinancialReport（财务报表）

Phase 3 将添加：
- TechnicalIndicator（技术指标）
- ValuationMetric（估值指标）
