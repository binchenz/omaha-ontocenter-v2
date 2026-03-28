# Financial Ontology 设计评估报告

## 当前设计概览

**已有对象（11个）：**
- 基础数据：Stock, DailyQuote, Industry
- 估值：ValuationMetric
- 财务三表：IncomeStatement, BalanceSheet, CashFlow
- 财务指标：FinancialIndicator
- 板块：Sector, SectorMember
- 技术指标：TechnicalIndicator

**核心能力：**
- 语义类型格式化（percentage, currency_cny, date等）
- 计算属性（dupont_roe, financial_health_score等）
- 默认过滤器（自动过滤退市股票）
- 聚合查询（count, avg, max, min, sum）

---

## 投资者日常需求覆盖度分析

### ✅ 已覆盖（70%）

**1. 选股筛选**
- 按行业/地区筛选 ✅
- 按估值指标筛选（PE/PB/股息率）✅
- 按财务指标筛选（ROE/毛利率/负债率）✅
- 按板块筛选 ✅

**2. 个股分析**
- 基本信息 ✅
- 估值指标 ✅
- 财务三表 ✅
- 技术指标 ✅

**3. 行业对比**
- 同行业股票列表 ✅
- 财务指标横向对比 ✅（通过多次查询）

---

## ❌ 缺失的关键功能（30%）

### 1. 持仓管理（0%覆盖）
**投资者痛点：**
- 无法保存自选股列表
- 无法跟踪持仓成本、盈亏
- 无法设置价格提醒

**缺失对象：**
- `Portfolio` - 投资组合
- `Position` - 持仓记录
- `Transaction` - 交易记录
- `PriceAlert` - 价格提醒

### 2. 资金流向（0%覆盖）
**投资者痛点：**
- 看不到主力资金进出
- 不知道北向资金持仓
- 龙虎榜数据缺失

**缺失对象：**
- `MoneyFlow` - 资金流向（大单、中单、小单）
- `NorthboundHolding` - 北向资金持仓
- `TopList` - 龙虎榜数据

### 3. 市场全局（20%覆盖）
**投资者痛点：**
- 没有大盘指数数据（上证、深证、创业板）
- 看不到市场情绪指标（涨跌家数、涨停跌停数）
- 缺少行业资金流向

**缺失对象：**
- `Index` - 指数行情（上证指数、深证成指等）
- `MarketSentiment` - 市场情绪（涨跌家数、涨停板数）
- `IndustryMoneyFlow` - 行业资金流向

### 4. 新闻/公告（0%覆盖）
**投资者痛点：**
- 看不到公司公告（业绩预告、分红、重组）
- 缺少新闻舆情

**缺失对象：**
- `Announcement` - 公司公告
- `News` - 新闻资讯

### 5. 分红/股本变动（0%覆盖）
**投资者痛点：**
- 不知道分红历史
- 看不到股本变动（增发、回购）

**缺失对象：**
- `Dividend` - 分红记录
- `ShareChange` - 股本变动

---

## 改进建议（按优先级）

### P0 - 必须补充（影响80%用户）

**1. 持仓管理模块**
```yaml
- Portfolio (投资组合)
  - id, user_id, name, created_at

- Position (持仓)
  - portfolio_id, ts_code, quantity, cost_price, current_price
  - profit_loss (计算属性)

- Transaction (交易记录)
  - portfolio_id, ts_code, type (buy/sell), quantity, price, date
```

**2. 资金流向**
```yaml
- MoneyFlow (资金流向)
  - ts_code, trade_date, buy_lg_amount, sell_lg_amount, net_mf_amount

- NorthboundHolding (北向资金)
  - ts_code, trade_date, hold_amount, hold_ratio
```

### P1 - 重要补充（影响50%用户）

**3. 市场全局**
```yaml
- Index (指数)
  - ts_code, name, trade_date, open, high, low, close, pct_chg

- MarketSentiment (市场情绪)
  - trade_date, up_count, down_count, limit_up_count, limit_down_count
```

**4. 分红数据**
```yaml
- Dividend (分红)
  - ts_code, ann_date, div_proc, stk_div, cash_div, ex_date
```

### P2 - 可选补充（影响20%用户）

**5. 公告/新闻**
```yaml
- Announcement (公告)
  - ts_code, ann_date, title, type

- News (新闻)
  - ts_code, pub_date, title, content, sentiment
```

---

## 现有设计的优点

1. **语义类型系统** - 自动格式化，用户体验好
2. **计算属性** - dupont_roe、financial_health_score 等高级指标
3. **关系完整** - Stock 与其他对象的关系清晰
4. **技术指标丰富** - MA、MACD、RSI、KDJ 全覆盖

---

## 总结

**当前覆盖度：70%**
- 基本面分析：✅ 90%
- 技术面分析：✅ 85%
- 持仓管理：❌ 0%
- 资金流向：❌ 0%
- 市场全局：⚠️ 20%

**建议优先级：**
1. P0：持仓管理 + 资金流向（解决最大痛点）
2. P1：指数 + 市场情绪（补全市场全局视角）
3. P2：公告/新闻（锦上添花）

补充这些后，覆盖度可达 **95%**，基本满足综合型投资者的日常需求。
