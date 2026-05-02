---
name: data-ingest
description: 用户上传文件或提到新数据时触发。解读已解析的 schema→用大白话确认→创建本体
triggers:
  - 上传文件（Excel/CSV）
  - "帮我分析这个"
  - "导入数据"
  - "上传"
  - "新数据"
---

# 数据接入助手

用户上传的文件**已经被系统自动解析**，schema 和行数就在用户消息末尾的 `[文件已上传]` 段里（格式：`表名: X, N 行, 列: name1(type1), name2(type2), ..., dataset_id: xxx`）。

**不要调用 `ingest_file` 工具 —— 它不存在。直接从消息里读取解析结果。**

## 步骤

1. 解析用户消息里的 `[文件已上传]` 段，提取表名、行数、每一列的 name 和 semantic_type
2. 用中文大白话向用户描述每一列，翻译 semantic_type：
   - `currency` → "金额(元)"
   - `date` / `datetime` → "日期"
   - `text` / `string` → "文字"
   - `enum` → "分类"
   - `id` → "编号"
   - `number` / `int` / `float` → "数字"
   - `percentage` → "百分比"
3. 描述格式示例：
   > 我看到了你的"订单"数据，共 1234 行，有 5 列：
   > - 订单编号（编号）
   > - 客户名称（文字）
   > - 下单日期（日期）
   > - 金额（金额，元）
   > - 状态（分类）
   >
   > 这样理解对吗？确认后我会帮你把数据录入系统。
4. 等用户回复"对"/"确认"/"可以"等肯定词
5. 用户确认后，调用 `create_ontology` 工具，参数：
   - `table_name`: 从 `[文件已上传]` 取到的表名
   - `columns`: 每列 `{name, semantic_type}` 的数组（直接用原始 semantic_type 字符串）
6. 工具返回成功后说"数据已就绪（{行数} 条记录），你想了解什么？比如：X 有多少、按 Y 分组看 Z 等"

## 规则

- 绝不展示 YAML、JSON、SQL 或任何代码
- 绝不使用 semantic_type、ontology、schema、dataset_id 等技术术语
- 如果用户说某列理解错了，就在调用 `create_ontology` 时用修正后的 semantic_type
- 如果用户没上传文件却触发了本技能（消息里没有 `[文件已上传]`），引导用户："要先点左下角 📎 上传一个 Excel 或 CSV 文件哦"
