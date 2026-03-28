# 持仓管理模块设计方案

## 目标
为投资者提供自选股管理、持仓跟踪、盈亏计算功能

---

## 新增对象设计

### 1. Portfolio（投资组合）

**用途：** 管理多个投资组合（如"价值投资组合"、"成长股组合"）

```yaml
- name: Portfolio
  datasource: postgres_db  # 存储在本地数据库
  table: portfolios
  description: 投资组合，用户可创建多个组合分别管理
  properties:
    - name: id
      type: integer
      description: 组合ID
    - name: user_id
      type: integer
      description: 用户ID
    - name: name
      type: string
      description: 组合名称，如"价值投资"、"自选股"
    - name: description
      type: string
      description: 组合描述
    - name: created_at
      type: datetime
      semantic_type: date
      description: 创建时间
    - name: updated_at
      type: datetime
      semantic_type: date
      description: 更新时间
```

### 2. Position（持仓）

**用途：** 记录每只股票的持仓情况

```yaml
- name: Position
  datasource: postgres_db
  table: positions
  description: 持仓记录，记录每只股票的数量、成本、当前市值
  properties:
    - name: id
      type: integer
      description: 持仓ID
    - name: portfolio_id
      type: integer
      description: 所属组合ID
    - name: ts_code
      type: string
      semantic_type: stock_code
      description: 股票代码
    - name: quantity
      type: integer
      description: 持仓数量（股）
    - name: cost_price
      type: number
      semantic_type: currency_cny
      description: 成本价（元/股）
    - name: current_price
      type: number
      semantic_type: currency_cny
      description: 当前价（元/股，实时更新）
    - name: created_at
      type: datetime
      semantic_type: date
    - name: updated_at
      type: datetime
      semantic_type: date

  computed_properties:
    - name: cost_amount
      expression: "{quantity} * {cost_price}"
      semantic_type: currency_cny
      description: 持仓成本（元）

    - name: market_value
      expression: "{quantity} * {current_price}"
      semantic_type: currency_cny
      description: 当前市值（元）

    - name: profit_loss
      expression: "({current_price} - {cost_price}) * {quantity}"
      semantic_type: currency_cny
      description: 浮动盈亏（元）

    - name: profit_loss_pct
      expression: "({current_price} - {cost_price}) / {cost_price} * 100"
      semantic_type: percentage
      description: 盈亏比例（%）

### 3. Transaction（交易记录）

**用途：** 记录买入/卖出历史

```yaml
- name: Transaction
  datasource: postgres_db
  table: transactions
  description: 交易记录，记录每笔买入/卖出操作
  properties:
    - name: id
      type: integer
    - name: portfolio_id
      type: integer
    - name: ts_code
      type: string
      semantic_type: stock_code
    - name: type
      type: string
      description: 交易类型：buy/sell
    - name: quantity
      type: integer
      description: 交易数量（股）
    - name: price
      type: number
      semantic_type: currency_cny
      description: 交易价格（元/股）
    - name: amount
      type: number
      semantic_type: currency_cny
      description: 交易金额（元）
    - name: fee
      type: number
      semantic_type: currency_cny
      description: 手续费（元）
    - name: trade_date
      type: string
      semantic_type: date
      description: 交易日期
    - name: note
      type: string
      description: 备注
```

### 4. Watchlist（自选股）

**用途：** 轻量级自选股列表（不记录持仓）

```yaml
- name: Watchlist
  datasource: postgres_db
  table: watchlist
  description: 自选股列表，用于关注但未持仓的股票
  properties:
    - name: id
      type: integer
    - name: user_id
      type: integer
    - name: ts_code
      type: string
      semantic_type: stock_code
    - name: added_at
      type: datetime
      semantic_type: date
    - name: note
      type: string
      description: 备注（如"等待回调到50元"）
```

---

## 关系设计

```yaml
relationships:
  - name: portfolio_positions
    from_object: Portfolio
    to_object: Position
    type: one_to_many
    join_condition:
      from_field: id
      to_field: portfolio_id

  - name: portfolio_transactions
    from_object: Portfolio
    to_object: Transaction
    type: one_to_many
    join_condition:
      from_field: id
      to_field: portfolio_id

  - name: position_stock
    from_object: Position
    to_object: Stock
    type: many_to_one
    join_condition:
      from_field: ts_code
      to_field: ts_code
```

---

## 典型使用场景

### 场景1：查看持仓盈亏
```
查询 Position，关联 Stock 获取股票名称，
计算属性自动返回 profit_loss 和 profit_loss_pct
```

### 场景2：添加自选股
```
插入 Watchlist 记录
```

### 场景3：记录买入操作
```
1. 插入 Transaction (type=buy)
2. 更新或创建 Position（累加数量、重新计算成本价）
```

### 场景4：组合总览
```
查询 Portfolio 的所有 Position，
聚合计算总市值、总盈亏
```

---

## 实现优先级

**Phase 1（MVP）：**
- Watchlist（自选股）- 最简单，先满足"关注股票"需求
- Position（持仓）- 核心功能

**Phase 2：**
- Portfolio（多组合）
- Transaction（交易记录）

**Phase 3：**
- 价格提醒（PriceAlert）
- 持仓分析报表

---

## 下一步

需要我开始实现吗？建议从 **Watchlist** 开始，因为：
1. 最简单（只需一张表）
2. 不依赖其他模块
3. 可以快速验证整个流程
