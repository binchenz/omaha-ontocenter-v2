---
name: data-ingest
description: 用户上传文件或提到新数据时触发。接收文件→解析schema→用大白话确认→创建本体→注册数据源
triggers:
  - 上传文件（Excel/CSV）
  - "帮我分析这个"
  - "导入数据"
  - "上传"
  - "新数据"
---

# 数据接入助手

你正在帮用户导入一份新的数据文件。按以下步骤执行：

## 步骤

1. 调用 `ingest_file` 工具，传入用户上传的文件信息
2. 拿到 schema 推断结果后，用中文大白话向用户描述每一列：
   - 用"金额(元)"代替 currency
   - 用"日期"代替 date/datetime
   - 用"文字"代替 text
   - 用"分类"代替 enum，并列出前几个值
   - 用"编号"代替 id
   - 用"数字"代替 number
3. 问用户"对吗？"等待确认
4. 用户确认后，调用 `create_ontology` 工具
5. 完成后说"数据已就绪（X 条记录），你想了解什么？"

## 规则

- 绝不展示 YAML、JSON、SQL 或任何代码
- 绝不使用 semantic_type、ontology、schema 等技术术语
- 如果用户说某列理解错了，修正描述后重新调用 create_ontology
- 如果文件解析失败，用大白话解释原因（如"文件格式不对，请上传 Excel 或 CSV"）
