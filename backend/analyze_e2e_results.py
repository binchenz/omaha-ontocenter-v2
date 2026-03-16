"""
Analyze E2E test results in detail
"""
import json
from pathlib import Path

# Find the latest report
reports = list(Path(".").glob("e2e_test_report_*.json"))
if not reports:
    print("No test reports found")
    exit(1)

latest_report = max(reports, key=lambda p: p.stat().st_mtime)
print(f"Analyzing: {latest_report}\n")

with open(latest_report, 'r', encoding='utf-8') as f:
    results = json.load(f)

print("="*80)
print("端到端测试详细分析")
print("="*80)

for i, result in enumerate(results, 1):
    print(f"\n{'='*80}")
    print(f"场景 {i}: {result['scenario']}")
    print(f"{'='*80}")
    print(f"问题: {result['question']}")
    print(f"响应时间: {result['response_time']}秒")
    print(f"状态: {'✅ 通过' if result['success'] else '❌ 失败'}")

    # Agent response
    agent_resp = result.get('agent_response', {})
    message = agent_resp.get('message', '')
    print(f"\nAgent 回复:")
    print(f"  {message[:200]}...")

    # SQL queries
    sql = agent_resp.get('sql')
    if sql:
        print(f"\nSQL 查询:")
        print(f"  {sql}")

    # Data returned
    data_table = agent_resp.get('data_table', [])
    if data_table:
        print(f"\n返回数据: {len(data_table)} 行")
        if data_table:
            print(f"  示例: {list(data_table[0].keys())}")

    # Tool calls
    tool_calls = agent_resp.get('tool_calls', [])
    if tool_calls:
        print(f"\nTool Calls: {len(tool_calls)}")
        for tc in tool_calls:
            tool_name = tc.get('tool', 'unknown')
            args = tc.get('arguments', {})
            print(f"  - {tool_name}: {args}")

    # Validation results
    print(f"\n验证结果:")
    for check, passed in result.get('validation', {}).items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")

    # Errors
    if result.get('errors'):
        print(f"\n错误:")
        for err in result['errors']:
            print(f"  - {err}")

# Summary
print(f"\n{'='*80}")
print("总结")
print(f"{'='*80}")

total = len(results)
passed = sum(1 for r in results if r['success'])
failed = total - passed

print(f"\n总场景数: {total}")
print(f"通过: {passed} ({passed/total*100:.1f}%)")
print(f"失败: {failed} ({failed/total*100:.1f}%)")

# Performance
response_times = [r['response_time'] for r in results if r['response_time'] > 0]
print(f"\n性能:")
print(f"  平均: {sum(response_times)/len(response_times):.2f}秒")
print(f"  最快: {min(response_times):.2f}秒")
print(f"  最慢: {max(response_times):.2f}秒")

# Timeout analysis
timeout_count = sum(1 for r in results if '超时' in r.get('agent_response', {}).get('message', ''))
print(f"\n超时场景: {timeout_count}/{total}")

# SQL generation analysis
sql_count = sum(1 for r in results if r.get('agent_response', {}).get('sql'))
print(f"生成SQL: {sql_count}/{total}")

# Data return analysis
data_count = sum(1 for r in results if r.get('agent_response', {}).get('data_table'))
print(f"返回数据: {data_count}/{total}")
