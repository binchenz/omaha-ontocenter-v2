# Omaha OntoCenter 部署状态

## 部署信息

- **服务器**: 69.5.23.70
- **API 端点**: http://69.5.23.70/api/public/v1
- **数据库**: PostgreSQL (5493 条股票记录已同步)
- **部署时间**: 2026-03-27
- **状态**: ✅ 运行中

## API 访问

### 认证
```bash
Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM
```

### 可用端点

1. **列出对象**
   ```bash
   curl -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
     http://69.5.23.70/api/public/v1/objects
   ```

2. **获取对象架构**
   ```bash
   curl -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
     http://69.5.23.70/api/public/v1/schema/Stock
   ```

3. **查询数据**
   ```bash
   curl -X POST http://69.5.23.70/api/public/v1/query \
     -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
     -H "Content-Type: application/json" \
     -d '{"object_type":"Stock","selected_columns":["ts_code","name","industry"],"limit":10}'
   ```

## Claude Code 集成

Skill 文件位置: `~/.claude/skills/omaha-cloud-test/skill.md`

使用方法：
```
查找所有银行股
```

## 监控建议

### 速率限制注意事项

Tushare API 有严格的调用频率限制：
- 免费版：每分钟约 200 次调用
- 建议监控频率：**每小时 1 次**或更低
- 避免频繁的数据查询测试

### 推荐监控方案

**方案 1：低频完整检查（推荐）**
- 频率：每 2 小时
- 检查内容：服务响应 + 简单数据查询
- 适用场景：生产环境稳定运行

**方案 2：高频轻量检查**
- 频率：每 30 分钟
- 检查内容：仅检查服务响应（不查询数据）
- 适用场景：需要快速发现服务宕机

## 当前问题

### Tushare API 速率限制
- **状态**: 激活中
- **原因**: 之前的频繁测试（每 10 分钟）
- **恢复时间**: 15-30 分钟
- **解决方案**: 等待自然重置，降低检查频率

## 验证清单

- [x] 服务部署完成
- [x] 数据库连接正常
- [x] 股票数据已同步（5493 条）
- [x] API 认证工作正常
- [x] 服务响应正常
- [ ] 数据查询测试（等待速率限制重置）
- [x] Claude Code Skill 配置完成

## 下一步

1. 等待 15-30 分钟让 Tushare API 速率限制重置
2. 进行一次完整的数据查询测试
3. 设置合理的监控频率（建议每 2 小时）
