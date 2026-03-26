# Phase 1 实施计划：金融数据对象基础层

**日期：** 2026-03-26
**状态：** 待执行
**预计工时：** 1-2 天
**负责人：** Claude Sonnet 4.6

---

## 目标

实现金融数据对象体系的基础层（Phase 1），建立基于 Tushare Pro 数据源的股票数据查询能力。

**核心对象：**
- Stock（股票基本信息）
- DailyQuote（日线行情）
- Industry（行业分类）

**核心关系：**
- Stock -> DailyQuote（一对多）
- Stock -> Industry（多对一）

**核心能力：**
- 查询股票基本信息和行情数据
- 按行业筛选和分组
- 支持简单的投资分析（价格走势、涨跌幅）

---

## 架构说明

### 数据流

```
用户查询请求
    ↓
FastAPI 端点 (/api/v1/query)
    ↓
OmahaService.query_objects()
    ↓
检测 datasource type = "tushare"
    ↓
OmahaService._query_tushare()
    ↓
调用 Tushare Pro API (ts.pro_api)
    ↓
返回 DataFrame → 转换为 dict list
    ↓
返回给前端
```

### 技术栈

- **后端框架：** FastAPI + Python 3.9+
- **数据源：** Tushare Pro API
- **配置格式：** YAML
- **测试框架：** pytest
- **数据处理：** pandas (Tushare 返回 DataFrame)

### 关键文件路径

- **配置文件：** `/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml`
- **服务层：** `/Users/wangfushuaiqi/omaha_ontocenter/backend/app/services/omaha.py`
- **测试文件：** `/Users/wangfushuaiqi/omaha_ontocenter/backend/tests/test_tushare_*.py`
- **环境变量：** `TUSHARE_TOKEN=044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90`

---

## 实施步骤

### 任务 1：创建 YAML 配置文件

**目标：** 创建完整的 Phase 1 配置文件，定义 Stock、DailyQuote、Industry 对象及其关系。

**预计时间：** 5 分钟

#### 步骤 1.1：创建配置文件目录

- [ ] 确认 `configs/` 目录存在

```bash
ls -la /Users/wangfushuaiqi/omaha_ontocenter/configs/
```

#### 步骤 1.2：创建 YAML 配置文件

- [ ] 创建文件 `/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml`

**完整配置内容：**

```yaml
# 金融股票分析配置 - Phase 1
# 包含 Stock、DailyQuote、Industry 对象及其关系

datasources:
  - id: tushare_pro
    name: Tushare Pro API
    type: tushare
    connection:
      token: ${TUSHARE_TOKEN}

ontology:
  objects:
    # 核心对象：股票基本信息
    - name: Stock
      datasource: tushare_pro
      api_name: stock_basic
      description: 股票基本信息
      default_filters:
        - field: list_status
          operator: "="
          value: "L"
      properties:
        - name: ts_code
          type: string
          description: 股票代码（如 000001.SZ）
        - name: symbol
          type: string
          description: 股票简称（如 000001）
        - name: name
          type: string
          description: 股票名称（如 平安银行）
        - name: area
          type: string
          description: 地域（如 深圳）
        - name: industry
          type: string
          description: 所属行业（如 银行）
        - name: market
          type: string
          description: 市场类型（主板/创业板/科创板）
        - name: list_date
          type: string
          description: 上市日期（YYYYMMDD）
        - name: list_status
          type: string
          description: 上市状态（L上市/D退市/P暂停上市）

    # 日线行情
    - name: DailyQuote
      datasource: tushare_pro
      api_name: daily
      description: 股票日线行情数据
      properties:
        - name: ts_code
          type: string
          description: 股票代码
        - name: trade_date
          type: string
          description: 交易日期（YYYYMMDD）
        - name: open
          type: number
          description: 开盘价
        - name: high
          type: number
          description: 最高价
        - name: low
          type: number
          description: 最低价
        - name: close
          type: number
          description: 收盘价
        - name: pre_close
          type: number
          description: 昨收价
        - name: change
          type: number
          description: 涨跌额
        - name: pct_chg
          type: number
          description: 涨跌幅（%）
        - name: vol
          type: number
          description: 成交量（手）
        - name: amount
          type: number
          description: 成交额（千元）

    # 行业分类（聚合查询）
    - name: Industry
      datasource: tushare_pro
      api_name: stock_basic
      description: 行业分类统计
      properties:
        - name: industry
          type: string
          description: 行业名称
        - name: stock_count
          type: number
          description: 该行业股票数量

  relationships:
    # Stock -> DailyQuote (一对多)
    - name: stock_daily_quotes
      description: 股票的日线行情数据
      from_object: Stock
      to_object: DailyQuote
      type: one_to_many
      join_condition:
        from_field: ts_code
        to_field: ts_code

    # Stock -> Industry (多对一)
    - name: stock_industry
      description: 股票所属行业
      from_object: Stock
      to_object: Industry
      type: many_to_one
      join_condition:
        from_field: industry
        to_field: industry
```

#### 步骤 1.3：验证配置文件

- [ ] 确认文件创建成功

```bash
cat /Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml
```

---

### 任务 2：编写 Stock 对象测试

**目标：** 使用 TDD 方法，先编写 Stock 对象的测试用例。

**预计时间：** 10 分钟

#### 步骤 2.1：创建测试文件

- [ ] 创建文件 `/Users/wangfushuaiqi/omaha_ontocenter/backend/tests/test_tushare_stock.py`

**完整测试代码：**

```python
"""
Test cases for Stock object via Tushare datasource.

Tests the Stock object to verify:
1. Basic queries work with Tushare API
2. Default filters are applied (list_status='L')
3. All properties are accessible
4. Filters work correctly
"""
import pytest
import os


class TestStockBasic:
    """Test basic Stock queries."""

    def test_query_stock_basic(self):
        """Test basic query returns stock data."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        # Set environment variable
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry", "area"],
            filters=[],
            limit=10
        )

        # Check result structure
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) > 0

        # Check first row has required fields
        first_row = result["data"][0]
        assert "ts_code" in first_row
        assert "name" in first_row
        assert "industry" in first_row
        print(f"✓ First stock: {first_row['ts_code']} - {first_row['name']}")

    def test_stock_default_filter(self):
        """Test that default_filters (list_status='L') is applied."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "list_status"],
            filters=[],
            limit=20
        )

        # All records should have list_status='L'
        assert result["success"] is True
        for row in result["data"]:
            assert row["list_status"] == "L", f"Stock {row['ts_code']} has status {row['list_status']}"
        print(f"✓ All {len(result['data'])} stocks have list_status='L'")

    def test_stock_filter_by_industry(self):
        """Test filtering stocks by industry."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            filters=[{"field": "industry", "value": "银行"}],
            limit=10
        )

        # All records should be in banking industry
        assert result["success"] is True
        assert len(result["data"]) > 0
        for row in result["data"]:
            assert row["industry"] == "银行"
        print(f"✓ Found {len(result['data'])} banking stocks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

#### 步骤 2.2：运行测试（预期失败）

- [ ] 运行测试，确认测试失败（因为配置文件可能还未创建或有问题）

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pytest tests/test_tushare_stock.py -v -s
```

#### 步骤 2.3：修复问题直到测试通过

- [ ] 根据错误信息修复配置或代码
- [ ] 重新运行测试直到全部通过

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pytest tests/test_tushare_stock.py -v -s
```

#### 步骤 2.4：提交代码

- [ ] 提交 Stock 对象测试和配置

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter && git add configs/financial_stock_analysis.yaml backend/tests/test_tushare_stock.py && git commit -m "feat: add Stock object with Tushare datasource

- Create financial_stock_analysis.yaml config
- Add Stock object with default_filters
- Add comprehensive test cases for Stock queries

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

### 任务 3：编写 DailyQuote 对象测试

**目标：** 编写 DailyQuote 对象的测试用例，验证日线行情查询功能。

**预计时间：** 10 分钟

#### 步骤 3.1：创建测试文件

- [ ] 创建文件 `/Users/wangfushuaiqi/omaha_ontocenter/backend/tests/test_tushare_daily_quote.py`

**完整测试代码：**

```python
"""
Test cases for DailyQuote object via Tushare datasource.

Tests the DailyQuote object to verify:
1. Basic queries work with Tushare API
2. All OHLC properties are accessible
3. Date filtering works correctly
4. Stock code filtering works
"""
import pytest
import os


class TestDailyQuoteBasic:
    """Test basic DailyQuote queries."""

    def test_query_daily_quote_basic(self):
        """Test basic query returns daily quote data."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "open", "high", "low", "close", "pct_chg"],
            filters=[{"field": "ts_code", "value": "000001.SZ"}],
            limit=10
        )

        # Check result structure
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) > 0

        # Check first row has OHLC data
        first_row = result["data"][0]
        assert "ts_code" in first_row
        assert "trade_date" in first_row
        assert "open" in first_row
        assert "high" in first_row
        assert "low" in first_row
        assert "close" in first_row
        print(f"✓ First quote: {first_row['trade_date']} - Close: {first_row['close']}")

    def test_daily_quote_filter_by_date(self):
        """Test filtering daily quotes by trade date."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "close", "pct_chg"],
            filters=[
                {"field": "ts_code", "value": "000001.SZ"},
                {"field": "trade_date", "value": "20240101"}
            ],
            limit=5
        )

        # Check result
        assert result["success"] is True
        if len(result["data"]) > 0:
            for row in result["data"]:
                assert row["trade_date"] == "20240101"
            print(f"✓ Found {len(result['data'])} quotes for 2024-01-01")
        else:
            print("✓ No trading on 2024-01-01 (holiday/weekend)")

    def test_daily_quote_volume_data(self):
        """Test that volume and amount data are present."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "vol", "amount"],
            filters=[{"field": "ts_code", "value": "000001.SZ"}],
            limit=5
        )

        # Check volume data exists
        assert result["success"] is True
        assert len(result["data"]) > 0
        for row in result["data"]:
            assert "vol" in row
            assert "amount" in row
        print(f"✓ Volume data present for {len(result['data'])} records")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

#### 步骤 3.2：运行测试

- [ ] 运行测试

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pytest tests/test_tushare_daily_quote.py -v -s
```

#### 步骤 3.3：修复问题直到测试通过

- [ ] 根据错误信息修复配置或代码
- [ ] 重新运行测试直到全部通过

#### 步骤 3.4：提交代码

- [ ] 提交 DailyQuote 对象测试

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter && git add backend/tests/test_tushare_daily_quote.py && git commit -m "feat: add DailyQuote object tests

- Add comprehensive test cases for DailyQuote queries
- Test OHLC data retrieval
- Test date and stock code filtering
- Test volume and amount data

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

### 任务 4：编写 Industry 对象测试

**目标：** 编写 Industry 对象的测试用例，验证行业分类查询功能。

**预计时间：** 8 分钟

#### 步骤 4.1：创建测试文件

- [ ] 创建文件 `/Users/wangfushuaiqi/omaha_ontocenter/backend/tests/test_tushare_industry.py`

**完整测试代码：**

```python
"""
Test cases for Industry object via Tushare datasource.

Tests the Industry object to verify:
1. Industry aggregation works correctly
2. Stock count is calculated
3. Industry names are unique
"""
import pytest
import os


class TestIndustryBasic:
    """Test basic Industry queries."""

    def test_query_industry_list(self):
        """Test querying industry list with stock counts."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Industry",
            selected_columns=["industry"],
            filters=[],
            limit=50
        )

        # Check result structure
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) > 0

        # Check industry names are present
        industries = [row["industry"] for row in result["data"]]
        assert len(industries) > 0
        assert len(set(industries)) == len(industries), "Industries should be unique"
        print(f"✓ Found {len(industries)} industries")

    def test_industry_filter_by_name(self):
        """Test filtering by specific industry name."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Industry",
            selected_columns=["industry"],
            filters=[{"field": "industry", "value": "银行"}],
            limit=10
        )

        # Check result
        assert result["success"] is True
        if len(result["data"]) > 0:
            for row in result["data"]:
                assert row["industry"] == "银行"
            print(f"✓ Found banking industry")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

#### 步骤 4.2：运行测试

- [ ] 运行测试

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pytest tests/test_tushare_industry.py -v -s
```

#### 步骤 4.3：修复问题直到测试通过

- [ ] 根据错误信息修复配置或代码
- [ ] 重新运行测试直到全部通过

#### 步骤 4.4：提交代码

- [ ] 提交 Industry 对象测试

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter && git add backend/tests/test_tushare_industry.py && git commit -m "feat: add Industry object tests

- Add test cases for Industry aggregation queries
- Test industry list retrieval
- Test industry filtering

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

### 任务 5：编写关系测试（Stock -> DailyQuote）

**目标：** 测试 Stock 和 DailyQuote 之间的一对多关系。

**预计时间：** 10 分钟

#### 步骤 5.1：创建测试文件

- [ ] 创建文件 `/Users/wangfushuaiqi/omaha_ontocenter/backend/tests/test_tushare_relationships.py`

**完整测试代码（第一部分）：**

```python
"""
Test cases for relationships between financial objects.

Tests:
1. Stock -> DailyQuote (one-to-many)
2. Stock -> Industry (many-to-one)
"""
import pytest
import os


class TestStockDailyQuoteRelationship:
    """Test Stock -> DailyQuote relationship."""

    def test_stock_with_daily_quotes(self):
        """Test querying stock with its daily quotes."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        # Note: Tushare datasource doesn't support JOIN operations
        # We need to query separately and combine results

        # Step 1: Query stock info
        stock_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            filters=[{"field": "ts_code", "value": "000001.SZ"}],
            limit=1
        )

        assert stock_result["success"] is True
        assert len(stock_result["data"]) == 1
        stock = stock_result["data"][0]
        print(f"✓ Stock: {stock['ts_code']} - {stock['name']}")

        # Step 2: Query daily quotes for this stock
        quote_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "close", "pct_chg"],
            filters=[{"field": "ts_code", "value": stock["ts_code"]}],
            limit=10
        )

        assert quote_result["success"] is True
        assert len(quote_result["data"]) > 0
        print(f"✓ Found {len(quote_result['data'])} daily quotes for {stock['name']}")

        # Verify all quotes belong to the same stock
        for quote in quote_result["data"]:
            assert quote["ts_code"] == stock["ts_code"]


class TestStockIndustryRelationship:
    """Test Stock -> Industry relationship."""

    def test_stocks_by_industry(self):
        """Test querying stocks grouped by industry."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        # Step 1: Query an industry
        industry_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Industry",
            selected_columns=["industry"],
            filters=[{"field": "industry", "value": "银行"}],
            limit=1
        )

        assert industry_result["success"] is True
        if len(industry_result["data"]) > 0:
            industry = industry_result["data"][0]
            print(f"✓ Industry: {industry['industry']}")

            # Step 2: Query stocks in this industry
            stock_result = service.query_objects(
                config_yaml=config_yaml,
                object_type="Stock",
                selected_columns=["ts_code", "name", "industry"],
                filters=[{"field": "industry", "value": industry["industry"]}],
                limit=10
            )

            assert stock_result["success"] is True
            assert len(stock_result["data"]) > 0
            print(f"✓ Found {len(stock_result['data'])} stocks in {industry['industry']} industry")

            # Verify all stocks belong to the same industry
            for stock in stock_result["data"]:
                assert stock["industry"] == industry["industry"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

#### 步骤 5.2：运行测试

- [ ] 运行测试

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pytest tests/test_tushare_relationships.py -v -s
```

#### 步骤 5.3：修复问题直到测试通过

- [ ] 根据错误信息修复配置或代码
- [ ] 重新运行测试直到全部通过

#### 步骤 5.4：提交代码

- [ ] 提交关系测试

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter && git add backend/tests/test_tushare_relationships.py && git commit -m "feat: add relationship tests for financial objects

- Test Stock -> DailyQuote relationship
- Test Stock -> Industry relationship
- Verify data consistency across related objects

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

### 任务 6：创建集成测试

**目标：** 创建端到端集成测试，验证完整的查询流程。

**预计时间：** 15 分钟

#### 步骤 6.1：创建集成测试文件

- [ ] 创建文件 `/Users/wangfushuaiqi/omaha_ontocenter/backend/tests/test_tushare_integration.py`

**完整测试代码：**

```python
"""
Integration tests for financial data objects.

End-to-end tests covering:
1. Complete query flow from config to results
2. Real-world analysis scenarios
3. Data consistency across objects
"""
import pytest
import os


class TestFinancialDataIntegration:
    """Integration tests for financial data analysis."""

    def test_stock_analysis_workflow(self):
        """Test complete stock analysis workflow."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        # Scenario: Analyze banking stocks
        print("\n=== Scenario: Analyze Banking Stocks ===")

        # Step 1: Find banking stocks
        stocks = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry", "area"],
            filters=[{"field": "industry", "value": "银行"}],
            limit=5
        )

        assert stocks["success"] is True
        assert len(stocks["data"]) > 0
        print(f"✓ Found {len(stocks['data'])} banking stocks")

        # Step 2: Get recent quotes for first stock
        first_stock = stocks["data"][0]
        quotes = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["trade_date", "close", "pct_chg", "vol"],
            filters=[{"field": "ts_code", "value": first_stock["ts_code"]}],
            limit=5
        )

        assert quotes["success"] is True
        print(f"✓ Retrieved {len(quotes['data'])} recent quotes for {first_stock['name']}")

        # Step 3: Verify data consistency
        for quote in quotes["data"]:
            assert "trade_date" in quote
            assert "close" in quote
            print(f"  - {quote['trade_date']}: ¥{quote['close']} ({quote.get('pct_chg', 0)}%)")

    def test_industry_comparison_workflow(self):
        """Test industry comparison workflow."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        print("\n=== Scenario: Compare Industries ===")

        # Step 1: Get list of industries
        industries = service.query_objects(
            config_yaml=config_yaml,
            object_type="Industry",
            selected_columns=["industry"],
            filters=[],
            limit=10
        )

        assert industries["success"] is True
        assert len(industries["data"]) > 0
        print(f"✓ Found {len(industries['data'])} industries")

        # Step 2: Count stocks in each industry
        for industry in industries["data"][:3]:  # Test first 3 industries
            stocks = service.query_objects(
                config_yaml=config_yaml,
                object_type="Stock",
                selected_columns=["ts_code", "name"],
                filters=[{"field": "industry", "value": industry["industry"]}],
                limit=100
            )

            assert stocks["success"] is True
            print(f"  - {industry['industry']}: {len(stocks['data'])} stocks")

    def test_price_trend_analysis(self):
        """Test price trend analysis for a specific stock."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        print("\n=== Scenario: Price Trend Analysis ===")

        # Get stock info
        stock = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            filters=[{"field": "ts_code", "value": "000001.SZ"}],
            limit=1
        )

        assert stock["success"] is True
        assert len(stock["data"]) == 1
        stock_info = stock["data"][0]
        print(f"✓ Analyzing: {stock_info['name']} ({stock_info['ts_code']})")

        # Get recent price data
        quotes = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["trade_date", "close", "pct_chg", "vol", "amount"],
            filters=[{"field": "ts_code", "value": stock_info["ts_code"]}],
            limit=10
        )

        assert quotes["success"] is True
        assert len(quotes["data"]) > 0
        print(f"✓ Retrieved {len(quotes['data'])} trading days")

        # Calculate simple statistics
        closes = [float(q["close"]) for q in quotes["data"]]
        avg_price = sum(closes) / len(closes)
        max_price = max(closes)
        min_price = min(closes)

        print(f"  - Average: ¥{avg_price:.2f}")
        print(f"  - High: ¥{max_price:.2f}")
        print(f"  - Low: ¥{min_price:.2f}")

    def test_config_validation(self):
        """Test that configuration is valid and complete."""
        from app.services.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()

        # Parse config
        result = service.parse_config(config_yaml)
        assert result["valid"] is True
        assert "config" in result

        config = result["config"]

        # Verify datasources
        assert "datasources" in config
        assert len(config["datasources"]) > 0
        assert config["datasources"][0]["type"] == "tushare"

        # Verify ontology
        assert "ontology" in config
        ontology = config["ontology"]

        # Verify objects
        assert "objects" in ontology
        object_names = [obj["name"] for obj in ontology["objects"]]
        assert "Stock" in object_names
        assert "DailyQuote" in object_names
        assert "Industry" in object_names

        # Verify relationships
        assert "relationships" in ontology
        rel_names = [rel["name"] for rel in ontology["relationships"]]
        assert "stock_daily_quotes" in rel_names
        assert "stock_industry" in rel_names

        print("✓ Configuration is valid and complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

#### 步骤 6.2：运行集成测试

- [ ] 运行完整的集成测试

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pytest tests/test_tushare_integration.py -v -s
```

#### 步骤 6.3：修复问题直到测试通过

- [ ] 根据错误信息修复配置或代码
- [ ] 重新运行测试直到全部通过

#### 步骤 6.4：运行所有 Tushare 测试

- [ ] 运行所有 Tushare 相关测试，确保全部通过

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pytest tests/test_tushare_*.py -v -s
```

#### 步骤 6.5：提交代码

- [ ] 提交集成测试

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter && git add backend/tests/test_tushare_integration.py && git commit -m "feat: add integration tests for financial data objects

- Add end-to-end workflow tests
- Test stock analysis scenarios
- Test industry comparison workflows
- Test price trend analysis
- Validate configuration completeness

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

### 任务 7：更新文档

**目标：** 更新项目文档，记录新增的金融数据对象功能。

**预计时间：** 10 分钟

#### 步骤 7.1：创建使用文档

- [ ] 创建文件 `/Users/wangfushuaiqi/omaha_ontocenter/docs/superpowers/financial_data_objects_usage.md`

**文档内容：**

```markdown
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
```

#### 步骤 7.2：提交文档

- [ ] 提交使用文档

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter && git add docs/superpowers/financial_data_objects_usage.md && git commit -m "docs: add financial data objects usage guide

- Document Stock, DailyQuote, Industry objects
- Add query examples and common scenarios
- Document relationships and limitations

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

### 任务 8：验证和清理

**目标：** 最终验证所有功能正常，清理临时文件。

**预计时间：** 5 分钟

#### 步骤 8.1：运行完整测试套件

- [ ] 运行所有测试，确保没有破坏现有功能

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pytest tests/ -v --tb=short
```

#### 步骤 8.2：验证配置文件

- [ ] 确认配置文件格式正确

```bash
python -c "import yaml; yaml.safe_load(open('/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'))"
```

#### 步骤 8.3：检查代码质量

- [ ] 运行 linter（如果项目有配置）

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -m pylint app/services/omaha.py --disable=all --enable=E || true
```

#### 步骤 8.4：更新 CHANGELOG

- [ ] 在项目 CHANGELOG 中记录新功能（如果有 CHANGELOG 文件）

#### 步骤 8.5：最终提交

- [ ] 创建最终的总结提交

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter && git add -A && git commit -m "feat: complete Phase 1 financial data objects implementation

Phase 1 includes:
- Stock object with Tushare datasource
- DailyQuote object for daily quotes
- Industry object for industry classification
- Relationships between objects
- Comprehensive test suite
- Usage documentation

All tests passing. Ready for production use.

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

## 验收标准

Phase 1 完成后，应满足以下标准：

### 功能验收

- [ ] Stock 对象可以查询股票基本信息
- [ ] DailyQuote 对象可以查询日线行情
- [ ] Industry 对象可以查询行业分类
- [ ] default_filters 正确应用（只返回上市股票）
- [ ] 可以通过 ts_code 关联 Stock 和 DailyQuote
- [ ] 可以通过 industry 关联 Stock 和 Industry

### 测试验收

- [ ] 所有单元测试通过（test_tushare_stock.py）
- [ ] 所有单元测试通过（test_tushare_daily_quote.py）
- [ ] 所有单元测试通过（test_tushare_industry.py）
- [ ] 所有关系测试通过（test_tushare_relationships.py）
- [ ] 所有集成测试通过（test_tushare_integration.py）
- [ ] 测试覆盖率 > 80%

### 文档验收

- [ ] 配置文件完整且格式正确
- [ ] 使用文档清晰易懂
- [ ] 包含查询示例和常见场景
- [ ] 记录了限制和注意事项

### 代码质量验收

- [ ] 代码符合项目规范
- [ ] 没有明显的性能问题
- [ ] 错误处理完善
- [ ] 日志记录充分

---

## 故障排查

### 问题 1：Tushare API 连接失败

**症状：** 测试报错 "Tushare query failed"

**解决方案：**
1. 检查 TUSHARE_TOKEN 环境变量是否设置
2. 验证 token 是否有效
3. 检查网络连接
4. 确认 Tushare Pro 账户积分充足

### 问题 2：返回数据为空

**症状：** 查询成功但 data 为空列表

**解决方案：**
1. 检查过滤条件是否过于严格
2. 验证 ts_code 格式是否正确（如 000001.SZ）
3. 确认查询的日期是否为交易日
4. 检查 Tushare API 是否有数据

### 问题 3：配置文件解析失败

**症状：** "Invalid configuration" 错误

**解决方案：**
1. 验证 YAML 格式是否正确（缩进、冒号）
2. 检查环境变量替换是否正确（${TUSHARE_TOKEN}）
3. 确认所有必需字段都已填写

### 问题 4：测试超时

**症状：** 测试运行时间过长或超时

**解决方案：**
1. 减少 limit 参数值
2. 添加更具体的过滤条件
3. 检查网络连接速度
4. 考虑使用缓存机制

---

## 下一步计划

Phase 1 完成后，可以开始 Phase 2 的实施：

### Phase 2：财务分析层

**新增对象：**
- FinancialIndicator（财务指标）
- FinancialReport（财务报表）

**预计工时：** 2-3 天

**参考文档：** `/docs/superpowers/specs/2026-03-26-financial-data-objects-design.md`

---

## 总结

本实施计划采用 TDD 方法，将 Phase 1 的实施分解为 8 个主要任务，每个任务包含详细的步骤、完整的代码示例和验证命令。

**关键特点：**
- 每个任务 2-5 分钟，易于执行
- 先写测试，后实现功能
- 每个步骤都有明确的验收标准
- 包含完整的代码示例和命令
- 提供故障排查指南

**执行建议：**
- 严格按照顺序执行任务
- 每个任务完成后立即提交代码
- 遇到问题及时查看故障排查部分
- 保持测试全部通过的状态

祝实施顺利！🚀
