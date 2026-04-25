# Phase 3：主动 AI — 健康规则引擎 + AI 洞察

## 1. 目标

让 AI 从"被动问答"变成"主动业务伙伴"。系统持续监控业务健康指标，发现异常时生成自然语言洞察，用户打开系统就能看到 AI 的主动分析。

这是从"传统 SaaS + AI"到"AI 原生"的关键转折点。

## 2. 范围

**包含：**
- 健康规则评估引擎（定时执行，对比阈值）
- 告警事件持久化
- LLM 驱动的洞察生成（把原始告警翻译成业务语言）
- Dashboard 页面（告警 + 洞察卡片）
- Agent 工具扩展（detect_anomaly、get_recent_alerts）
- Agent 对话自动注入最近告警

**不包含（后续迭代）：**
- WebSocket 实时推送
- 邮件/企业微信等外部通知渠道
- 环境 AI（各页面嵌入式建议）
- 告警偏好设置（频率、渠道自定义）

## 3. 数据模型

### 3.1 AlertEvent（告警事件）

```python
class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: int (PK)
    tenant_id: int (FK → tenants.id, index)
    object_id: int (FK → ontology_objects.id, index)
    rule_id: int (FK → health_rules.id, index)
    project_id: int (FK → projects.id, index)

    severity: str  # "warning" | "critical"
    metric_value: float  # 实际计算值
    threshold_value: str  # 阈值表达式原文
    message: str  # 规则的 advice 字段
    ai_insight: str | None  # LLM 生成的分析（可选，由 InsightGenerator 回填）

    status: str  # "active" | "acknowledged" | "resolved"
    triggered_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
```

### 3.2 InsightCard（洞察卡片）

```python
class InsightCard(Base):
    __tablename__ = "insight_cards"

    id: int (PK)
    tenant_id: int (FK → tenants.id, index)
    project_id: int (FK → projects.id, index)

    title: str  # "本周退货率异常"
    content: str  # LLM 生成的完整分析
    source_type: str  # "health_rule" | "anomaly" | "trend"
    source_id: int | None  # 关联的 alert_event_id（可选）

    pinned: bool = False  # 用户钉选到 Dashboard
    created_at: datetime
    expires_at: datetime | None  # 过期自动隐藏，默认 7 天
```

### 3.3 关系说明

- 一个 AlertEvent 可以触发一个 InsightCard（1:1）
- 同一对象的多个 AlertEvent 可以合并成一个 InsightCard（N:1）
- InsightCard 独立于 AlertEvent 存在（anomaly/trend 类型无需关联告警）

## 4. 后端服务

### 4.1 HealthRuleEvaluator

职责：纯计算，评估健康规则是否违规。

```python
class HealthRuleEvaluator:
    def __init__(self, omaha_service: OmahaService):
        self.omaha = omaha_service

    def evaluate_object(self, object_def, rules, config) -> list[RuleViolation]:
        """评估一个对象的所有健康规则，返回违规列表"""
        # 对每条规则：
        # 1. 用 OmahaService 查询数据
        # 2. 执行聚合表达式（avg, sum, count, max, min）
        # 3. 对比 warning/critical 阈值
        # 4. 返回 RuleViolation(rule, severity, actual_value)
```

支持的聚合表达式：
- `avg(field)` — 平均值
- `sum(field)` — 求和
- `count(field)` — 计数
- `max(field)` / `min(field)` — 最大/最小值
- `count(field) where condition` — 条件计数（如 `count(*) where status='已取消'`）

阈值比较：解析 `> 3天`、`< 95%`、`>= 100` 等格式。

### 4.2 InsightGenerator

职责：调用 LLM，把原始告警翻译成自然语言洞察。

```python
class InsightGenerator:
    def generate(self, alerts: list[AlertEvent], context: ObjectContext) -> InsightCard:
        """将告警转化为用户可读的洞察卡片"""
        # Prompt 包含：
        # - 告警详情（指标、实际值、阈值、severity）
        # - 对象的 domain_knowledge
        # - 对象的 business_goals
        # - 最近的数据趋势（可选）
        #
        # LLM 输出：
        # - title: 简短标题
        # - content: 分析 + 可能原因 + 建议行动
```

Prompt 设计原则：
- 用业务语言，不用技术术语
- 给出可能原因（结合 domain_knowledge）
- 给出具体建议（不是泛泛的"请关注"）
- 单个告警 → 单条洞察；同对象多个告警 → 合并成一条综合洞察

### 4.3 AlertScheduler

职责：定时调度健康规则评估。

```python
class AlertScheduler:
    def run(self, project_id: int):
        """一次完整的评估周期"""
        # 1. 加载项目的所有 ontology objects + health_rules
        # 2. 对每个对象调用 HealthRuleEvaluator.evaluate_object()
        # 3. 去重：同 rule + 同 severity + 24h 内已存在 → 跳过
        # 4. 写入新的 AlertEvent（status=active）
        # 5. 自动解决：之前 active 的告警，本次评估通过 → 标记 resolved
        # 6. 将新告警传给 InsightGenerator → 写入 InsightCard
```

调度策略：
- 复用现有 APScheduler 基础设施（`backend/app/services/scheduler.py`）
- 默认每小时执行一次
- 每个项目独立调度
- 支持手动触发（API 端点）

去重逻辑：
- 同一 rule_id + 同一 severity + 24 小时内已有 active 告警 → 不重复创建
- 如果 severity 升级（warning → critical）→ 创建新告警

自动解决：
- 本次评估中，某条规则不再违规 → 将对应的 active AlertEvent 标记为 resolved

## 5. API 端点

### 5.1 告警 API

```
GET  /api/v1/projects/{project_id}/alerts
     Query: severity, status, object_id, limit, offset
     Response: { items: AlertEvent[], total: int }

PUT  /api/v1/projects/{project_id}/alerts/{alert_id}
     Body: { status: "acknowledged" | "resolved" }
     Response: AlertEvent

POST /api/v1/projects/{project_id}/alerts/evaluate
     触发一次手动评估，返回新产生的告警
     Response: { alerts: AlertEvent[], insights: InsightCard[] }
```

### 5.2 洞察 API

```
GET  /api/v1/projects/{project_id}/insights
     Query: pinned, source_type, limit, offset
     Response: { items: InsightCard[], total: int }

PUT  /api/v1/projects/{project_id}/insights/{insight_id}/pin
     Body: { pinned: boolean }
     Response: InsightCard
```

### 5.3 Dashboard 摘要 API

```
GET  /api/v1/projects/{project_id}/dashboard/summary
     Response: {
       health: { normal: int, warning: int, critical: int },
       recent_insights: InsightCard[],  # 最近 5 条
       ai_summary: str  # LLM 生成的一句话总结
     }
```

## 6. Agent 工具扩展

### 6.1 新增工具

**get_recent_alerts**
```json
{
  "name": "get_recent_alerts",
  "description": "获取项目最近的告警事件",
  "parameters": {
    "severity": "warning | critical | all",
    "limit": 10
  }
}
```

**detect_anomaly**
```json
{
  "name": "detect_anomaly",
  "description": "对指定对象的指定指标做趋势分析，检测异常",
  "parameters": {
    "object_name": "订单",
    "metric": "退货率",
    "period": "7d | 30d | 90d"
  }
}
```

detect_anomaly 实现逻辑：
1. 查询指定周期的数据
2. 计算均值和标准差
3. 最近值偏离均值超过 2 个标准差 → 标记为异常
4. 返回趋势数据 + 异常标记 + 变化幅度

### 6.2 Agent System Prompt 注入

Agent 初始化时，自动在 system prompt 末尾追加：

```
## 当前告警状态
你所在项目有以下活跃告警：
- [WARNING] 订单.平均发货时间 = 5.2天（阈值: > 3天）
- [CRITICAL] 库存.缺货SKU数 = 23（阈值: > 10）

请在对话中适时提及这些告警，帮助用户关注业务健康状况。
```

这样用户问"最近怎么样"时，Agent 无需额外查询就能直接回应。

## 7. 前端 Dashboard 页面

替换现有的"即将推出"占位符，分三个区域：

### 7.1 AI 摘要条（顶部）

- 调用 `/dashboard/summary` API
- 显示健康状态计数（3 正常 / 1 警告 / 0 严重）
- 显示 LLM 生成的一句话摘要
- 背景色随最高 severity 变化（绿/黄/红）

### 7.2 洞察卡片流（中部）

- 调用 `/insights` API
- 钉选的卡片置顶，其余按时间倒序
- 每张卡片：标题、摘要（前 100 字）、severity 标签、时间、钉选按钮
- 点击展开完整内容
- 空状态："暂无洞察，系统正在监控中"

### 7.3 告警表格（底部）

- 调用 `/alerts` API
- 列：severity 图标、对象名、指标、实际值、阈值、状态、时间
- 筛选：severity、status
- 操作：确认（acknowledged）、标记解决（resolved）

## 8. 测试策略

### 8.1 单元测试

- HealthRuleEvaluator：各种表达式解析、阈值比较、边界情况
- InsightGenerator：mock LLM，验证 prompt 构建和输出解析
- AlertScheduler：去重逻辑、自动解决逻辑

### 8.2 集成测试

- 完整评估周期：创建对象 + 规则 → 触发评估 → 验证告警和洞察生成
- API 端点：CRUD 操作、权限验证、分页

### 8.3 前端测试

- Dashboard 组件渲染（mock API）
- 钉选/确认交互
