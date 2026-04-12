# 硕士生分享 PPT 制作计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 制作一套可直接用于 15 分钟硕士生分享的完整 PPT（12页），配套演示数据和备用录屏

**Architecture:** 分三个独立阶段：先准备演示环境和数据（保证演示可用），再制作视觉资产（图表），最后制作 PPT 正文内容。每个阶段可独立验证。

**Tech Stack:** Python（生成模拟数据）、SQLite、任意 PPT 工具（PowerPoint/Keynote/Google Slides）

**Spec:** `docs/superpowers/specs/2026-04-12-university-talk-design.md`

---

## Chunk 1：演示环境准备

### Task 1：生成模拟演示数据

**Files:**
- Create: `scripts/demo/seed_demo_data.py`
- Modify: `backend/omaha.db`（写入模拟数据）

- [ ] **Step 1：创建演示数据脚本**

创建 `scripts/demo/seed_demo_data.py`，生成 30 条模拟股票记录，其中至少 15 条 ROE > 15%：

```python
#!/usr/bin/env python3
"""
Seed mock stock + financial data for the university talk demo.
Run from repo root: python scripts/demo/seed_demo_data.py
"""
import sqlite3
import random
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../backend/demo.db")

STOCKS = [
    ("000001.SZ", "平安银行", "银行", "广东"),
    ("000002.SZ", "万科A", "房地产", "广东"),
    ("000063.SZ", "中兴通讯", "通信设备", "广东"),
    ("000333.SZ", "美的集团", "家用电器", "广东"),
    ("000651.SZ", "格力电器", "家用电器", "广东"),
    ("000858.SZ", "五粮液", "食品饮料", "四川"),
    ("002415.SZ", "海康威视", "电子", "浙江"),
    ("600000.SH", "浦发银行", "银行", "上海"),
    ("600036.SH", "招商银行", "银行", "广东"),
    ("600276.SH", "恒瑞医药", "医药生物", "江苏"),
    ("600309.SH", "万华化学", "化工", "山东"),
    ("600519.SH", "贵州茅台", "食品饮料", "贵州"),
    ("600900.SH", "长江电力", "公用事业", "湖北"),
    ("601012.SH", "隆基绿能", "电气设备", "陕西"),
    ("601318.SH", "中国平安", "保险", "广东"),
    ("601328.SH", "交通银行", "银行", "上海"),
    ("601398.SH", "工商银行", "银行", "北京"),
    ("601628.SH", "中国人寿", "保险", "北京"),
    ("601888.SH", "中国中免", "商业贸易", "北京"),
    ("603288.SH", "海天味业", "食品饮料", "广东"),
    ("300059.SZ", "东方财富", "非银金融", "上海"),
    ("300750.SZ", "宁德时代", "电气设备", "福建"),
    ("688111.SH", "金山办公", "计算机", "北京"),
    ("688169.SH", "石头科技", "家用电器", "北京"),
    ("002594.SZ", "比亚迪", "汽车", "广东"),
    ("600887.SH", "伊利股份", "食品饮料", "内蒙古"),
    ("601166.SH", "兴业银行", "银行", "福建"),
    ("000538.SZ", "云南白药", "医药生物", "云南"),
    ("600030.SH", "中信证券", "非银金融", "广东"),
    ("600690.SH", "海尔智家", "家用电器", "山东"),
]

# 20 high-ROE stocks (ROE > 15%), 10 low-ROE stocks
HIGH_ROE = [
    (22.3, 8.5), (19.8, 6.2), (18.5, 5.2), (21.0, 7.8), (17.6, 9.1),
    (16.2, 12.3), (25.4, 15.6), (18.9, 11.2), (23.1, 9.8), (20.5, 7.3),
    (16.8, 6.9), (24.7, 32.1), (15.3, 14.2), (17.2, 18.9), (19.1, 10.5),
    (22.8, 8.1), (16.5, 5.8), (18.3, 7.4), (20.2, 13.7), (15.8, 11.9),
]
LOW_ROE = [
    (8.2, 25.3), (5.6, 42.1), (11.3, 19.8), (9.7, 31.5), (7.1, 28.9),
    (4.3, 55.2), (12.8, 22.4), (3.9, 68.7), (10.5, 16.3), (6.4, 38.1),
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create minimal tables matching Omaha's expected schema
    c.execute("""
        CREATE TABLE IF NOT EXISTS stock_basic (
            ts_code TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            list_status TEXT DEFAULT 'L',
            area TEXT DEFAULT '广东',
            market TEXT DEFAULT 'A',
            list_date TEXT DEFAULT '20100101'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS fina_indicator (
            ts_code TEXT,
            end_date TEXT,
            roe REAL,
            roa REAL,
            grossprofit_margin REAL,
            netprofit_margin REAL,
            debt_to_assets REAL,
            PRIMARY KEY (ts_code, end_date)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_basic (
            ts_code TEXT,
            trade_date TEXT,
            pe_ttm REAL,
            pb REAL,
            ps_ttm REAL,
            dv_ratio REAL,
            total_mv REAL,
            PRIMARY KEY (ts_code, trade_date)
        )
    """)

    metrics = HIGH_ROE + LOW_ROE
    for i, (ts_code, name, industry, area) in enumerate(STOCKS):
        roe, pe = metrics[i]
        # stock_basic
        c.execute("INSERT OR REPLACE INTO stock_basic VALUES (?,?,?,?,?,?,?)",
                  (ts_code, name, industry, 'L', area, 'A', '20100101'))
        # fina_indicator
        c.execute("INSERT OR REPLACE INTO fina_indicator VALUES (?,?,?,?,?,?,?)",
                  (ts_code, '20231231', roe, roe * 0.6,
                   round(random.uniform(25, 55), 1),
                   round(random.uniform(10, 30), 1),
                   round(random.uniform(30, 65), 1)))
        # daily_basic
        c.execute("INSERT OR REPLACE INTO daily_basic VALUES (?,?,?,?,?,?,?)",
                  (ts_code, '20240101', pe,
                   round(random.uniform(1.0, 5.0), 1),
                   round(random.uniform(2.0, 8.0), 1),
                   round(random.uniform(1.0, 4.0), 1),
                   round(random.uniform(500, 50000), 0)))

    conn.commit()
    conn.close()
    print(f"✅ Seeded 30 stocks into {DB_PATH}")
    print(f"   - 20 stocks with ROE > 15%")
    print(f"   - 10 stocks with ROE < 13%")

if __name__ == "__main__":
    seed()
```

- [ ] **Step 2：运行数据脚本，验证输出**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
mkdir -p scripts/demo
python scripts/demo/seed_demo_data.py
```

期望输出：
```
✅ Seeded 30 stocks into .../backend/demo.db
   - 20 stocks with ROE > 15%
   - 10 stocks with ROE < 13%
```

- [ ] **Step 3：验证数据库内容**

```bash
sqlite3 backend/demo.db "SELECT ts_code, name, roe FROM fina_indicator WHERE roe > 15 ORDER BY roe DESC LIMIT 5;"
```

期望：返回至少 5 行，ROE 均 > 15。

- [ ] **Step 4：提交脚本**

```bash
git add scripts/demo/seed_demo_data.py
git commit -m "feat: add demo data seed script for university talk"
```

---

### Task 2：配置演示专用项目

**目的：** 让 Chat 演示使用 demo.db，而非生产数据库，避免脏数据影响演示效果。

- [ ] **Step 1：在 Omaha 后台创建演示项目**

启动后端（如未运行）：
```bash
cd backend && venv311/bin/python -m uvicorn app.main:app --reload --port 8000
```

登录并创建演示项目（用 admin 账号或 demo 账号）：
- 打开 `http://localhost:5173`
- 新建项目，名称："大学分享演示"
- 在 Config 页粘贴以下 YAML：

```yaml
datasources:
  - id: demo_sqlite
    name: 演示数据库
    type: sqlite
    connection:
      database: ./demo.db

ontology:
  objects:
    - name: Stock
      datasource: demo_sqlite
      table: stock_basic
      description: A股基本信息
      default_filters:
        - field: list_status
          operator: "="
          value: "L"
      properties:
        - name: ts_code
          type: string
          description: 股票代码
        - name: name
          type: string
          description: 股票名称
        - name: industry
          type: string
          description: 所属行业

    - name: FinancialIndicator
      datasource: demo_sqlite
      table: fina_indicator
      description: 财务指标
      properties:
        - name: ts_code
          type: string
          description: 股票代码
        - name: end_date
          type: string
          description: 报告期
        - name: roe
          type: float
          semantic_type: percentage
          description: 净资产收益率
        - name: roa
          type: float
          semantic_type: percentage
          description: 总资产收益率
        - name: grossprofit_margin
          type: float
          semantic_type: percentage
          description: 毛利率
        - name: netprofit_margin
          type: float
          semantic_type: percentage
          description: 净利润率

    - name: ValuationMetric
      datasource: demo_sqlite
      table: daily_basic
      description: 估值指标
      properties:
        - name: ts_code
          type: string
          description: 股票代码
        - name: pe_ttm
          type: float
          semantic_type: ratio
          description: 滚动市盈率
        - name: pb
          type: float
          semantic_type: ratio
          description: 市净率
        - name: dv_ratio
          type: float
          semantic_type: percentage
          description: 股息率
        - name: total_mv
          type: float
          semantic_type: large_number
          description: 总市值（万元）
```

- [ ] **Step 2：保存并验证配置**

点击"Validate"按钮，确认显示"Valid"。

- [ ] **Step 3：在 Explorer 页验证查询**

切换到 Explorer → Objects，选择 Stock，点击 Query，确认返回 30 条记录。

- [ ] **Step 4：验证演示核心查询**

在 Chat 页输入：
> "找出ROE大于15%的股票，按PE从低到高排列，取前10名"

确认 AI 调用 screen_stocks 并返回 ≥ 10 条结果，ROE 显示为百分比格式。

---

## Chunk 2：视觉资产制作

### Task 3：制作对象关系图（Slide 5）

**格式：** 导出为 PNG，尺寸 1920×1080，文件名 `slide5-ontology-graph.png`

- [ ] **Step 1：绘制对象关系图**

使用任意工具（draw.io / Figma / PPT 自带图形）绘制：

```
┌─────────┐              ┌──────────────────────┐              ┌───────────────────┐
│  Stock  │ ──ts_code──→ │  FinancialIndicator   │ ──ts_code──→ │  ValuationMetric  │
│         │              │                      │              │                   │
│ts_code  │              │roe: 百分比 (%)        │              │pe_ttm: 倍数 (x)   │
│name     │              │roa: 百分比 (%)        │              │pb: 倍数 (x)       │
│industry │              │grossprofit_margin: %  │              │dv_ratio: 百分比   │
└─────────┘              └──────────────────────┘              └───────────────────┘
```

关键标注：
- 箭头标签：`ts_code 关联`
- 每个字段右侧标注语义类型（用不同颜色区分：百分比=蓝色、倍数=橙色、分类=绿色）

- [ ] **Step 2：导出并命名**

```bash
mkdir -p docs/superpowers/assets
```

保存到 `docs/superpowers/assets/slide5-ontology-graph.png`

---

### Task 4：制作架构流程图（Slide 7）

**格式：** 导出为 PNG，尺寸 1920×540（宽幅），文件名 `slide7-architecture.png`

- [ ] **Step 1：绘制架构图**

从左到右五个方块，带箭头：

```
[YAML 配置]  →  [OmahaService]  →  [数据源]  →  [语义格式化]  →  [用户 / AI]
  定义对象         解析执行           SQLite       % ¥ 亿           Chat界面
  语义类型         查询构建           MySQL                        MCP接口
  关系映射         过滤排序           Tushare
```

底部添加注释：**"换一份 YAML = 换一个领域"**

- [ ] **Step 2：导出并命名**

保存到 `docs/superpowers/assets/slide7-architecture.png`

- [ ] **Step 3：提交资产目录**

```bash
git add docs/superpowers/assets/
git commit -m "docs: add visual assets for university talk slides 5 and 7"
```

---

## Chunk 3：PPT 正文制作

### Task 5：制作 PPT（12页）

**工具：** Keynote（Mac）/ PowerPoint / Google Slides，任选其一

- [ ] **Step 1：新建文件，设置主题**

- 比例：16:9
- 背景：深色（深灰 #1E1E2E 或黑色）+ 白色文字，现代简洁风格
- 字体：标题 36-40pt Bold，正文 24pt，代码 Menlo/Monaco 20pt
- 主色调：蓝色（#4F8EF7）用于高亮关键词

- [ ] **Step 2：逐页制作（按大纲）**

按 spec 文件 Slide 1-12 逐页制作，每页完成后核对 spec 要点：

**Slide 1（封面）：**
- 大标题居中："用本体论构建 AI 可理解的业务知识库"
- 副标题："Omaha OntoCenter 的设计与实践"
- 右下角：姓名、日期、单位

**Slide 2（开场问题）：**
- 全屏大字（60pt+）："AI 怎么理解'高ROE低PE的银行股'？"
- 下方三列：`自然语言查询` → `[?]` → `结果表格`（用图标表示）
- 底部小字过渡语（灰色）

**Slide 3（传统局限）：**
- 左右两列对比布局
- 左：SQL图标 + "硬编码，改需求=改代码"
- 右：气泡图标 + "Prompt不稳定，AI会猜错"
- 底部居中：红色文字"共同问题：缺乏业务语义层"

**Slide 4（本体论）：**
- 标题："本体论 = AI 的业务语义地图"
- 三行要点，带图标：Object / Property / Relationship
- 底部类比文字（斜体灰色）

**Slide 5（具体例子）：**
- 插入 `slide5-ontology-graph.png`（全屏或居中大图）
- 底部一行重点文字（蓝色高亮）

**Slide 6（YAML示例）：**
- 左半：代码块（深色背景 #282C34，等宽字体，语法高亮）
- 右半：两行注释说明（技术/非技术各一句）
- 底部警告小字："⚠️ 技术细节展示45秒，不展开"（speaker only，灰色极小字）

**Slide 7（架构）：**
- 插入 `slide7-architecture.png`（全幅）
- 标题区："配置驱动 = 换 YAML，换领域"

**Slide 8（演示）：**
- 顶部：输入框样式，显示查询语句
- 中部：工具调用参数展示（小字代码块）
- 底部：结果表格（至少6行，格式化显示）
- 角标：⚡ 现场演示 / 🎬 备用录屏

**Slide 9（背后机制）：**
- 四步流程竖排，带编号圆圈
- 第2步"Function Calling"文字加蓝色高亮框
- 底部结论（大字）："AI 有地图，不是在猜"

**Slide 10（可迁移性）：**
- 三列卡片布局（医疗/供应链/学术）
- 每列：行业图标 + 对象链 + 示例查询
- 底部："换一份 YAML = 新领域知识库"

**Slide 11（总结）：**
- 三条要点，每条一行，带序号
- 联系方式 / 项目地址（GitHub）
- 右下角 QR 码（可选）

**Slide 12（Q&A）：**
- 留白，大字："Q & A"
- 底部引导问题（斜体灰色小字）

- [ ] **Step 3：全局检查**

- [ ] 字体大小一致（标题36+，正文24+，代码20+）
- [ ] 对比度检查（深色背景+白字，可读性高）
- [ ] 12页页数正确
- [ ] 每页底部页码标注
- [ ] Slide 6 代码块语法高亮（YAML关键字着色）

- [ ] **Step 4：保存文件**

保存到 `docs/superpowers/assets/university-talk-2026.key`（或 .pptx / .pdf）

- [ ] **Step 5：导出 PDF 备份**

导出为 PDF（每页一张），保存到 `docs/superpowers/assets/university-talk-2026.pdf`

```bash
git add docs/superpowers/assets/
git commit -m "docs: add university talk PPT and PDF export"
```

---

## Chunk 4：排练与备用演示

### Task 6：录制备用演示视频

- [ ] **Step 1：确认演示环境就绪**

```bash
# 后端运行中（注意：健康检查路径是 /health，不是 /api/v1/health）
curl http://localhost:8000/health
# 期望：{"status": "healthy"}

# 演示查询：通过 UI 手动验证（API 需要 JWT token，直接在浏览器操作更简单）
# 打开 http://localhost:5173 → 大学分享演示项目 → Explorer → Objects
# 选择 FinancialIndicator，添加过滤器 roe >= 15，点击 Query
# 期望：返回 ≥ 10 条结果
```

- [ ] **Step 2：录制 Chat 演示视频（60-90秒）**

使用 QuickTime 或 OBS 录制屏幕：
1. 打开 `http://localhost:5173` → 进入"大学分享演示"项目 → Chat 页
2. 输入查询："找出ROE大于15%的股票，按PE从低到高排列，取前10名"
3. 等待 AI 响应（显示工具调用 + 格式化结果表格）
4. 缓慢滚动结果，确保摄像机可看清格式化数字

保存为 `docs/superpowers/assets/demo-backup.mp4`

- [ ] **Step 3：完整排练一遍，计时**

按 PPT 顺序过一遍，用手机计时，目标 ≤ 14 分钟（留1分钟缓冲）：
- 如超时：Slide 10（可迁移性）直接跳过
- 如提前：在 Slide 8 演示时放慢，多解释工具调用参数

- [ ] **Step 4：提交最终资产**

```bash
git add docs/superpowers/assets/
git commit -m "docs: add demo backup video and finalize university talk assets"
```

---

## 最终验收清单

分享前 30 分钟逐项确认：

- [ ] PPT 文件可正常打开，12页完整
- [ ] 演示后端运行：`curl http://localhost:8000/api/v1/health`
- [ ] 演示查询返回 ≥ 10 条结果（手动测试一次）
- [ ] Chat 界面登录成功，选中"大学分享演示"项目
- [ ] 备用视频 `demo-backup.mp4` 可播放
- [ ] Slide 6 代码高亮显示正常
- [ ] 投影仪/外接屏幕连接正常，分辨率 1920×1080

---

## 时间预估

| 任务 | 预估时间 |
|------|---------|
| Task 1：生成演示数据 | 20 分钟 |
| Task 2：配置演示项目 | 30 分钟 |
| Task 3：对象关系图 | 45 分钟 |
| Task 4：架构流程图 | 30 分钟 |
| Task 5：制作 PPT | 2-3 小时 |
| Task 6：录制+排练 | 45 分钟 |
| **合计** | **约 5-6 小时** |
