"""
Re-validate E2E test results with corrected logic
"""
import json
from pathlib import Path

def validate_expectations(response: dict, expectations: dict) -> dict:
    """Validate response against expectations"""
    validation = {}

    # Check if agent understood the query (not a timeout)
    if "understands_query" in expectations:
        message = response.get("message", "")
        validation["understands_query"] = (
            message is not None and
            len(message) > 10 and
            "超时" not in message
        )

    # Check if SQL was generated
    if "generates_sql" in expectations:
        validation["generates_sql"] = bool(response.get("sql"))

    # Check if specific objects were queried
    if "queries_objects" in expectations:
        expected_objects = expectations["queries_objects"]
        sql = response.get("sql", "")
        # Simple check: see if object name appears in SQL
        validation["queries_objects"] = all(
            obj.lower() in sql.lower() or
            f"dm_ppy_{obj.lower()}" in sql.lower()
            for obj in expected_objects
        )

    # Check if results were returned
    if "returns_results" in expectations:
        data_table = response.get("data_table", [])
        validation["returns_results"] = bool(data_table and len(data_table) > 0)

    # Check if specific keywords are in response
    if "contains_keywords" in expectations:
        keywords = expectations["contains_keywords"]
        message = response.get("message", "").lower()
        validation["contains_keywords"] = all(
            kw.lower() in message for kw in keywords
        )

    return validation

# Find the latest report
reports = list(Path(".").glob("e2e_test_report_*.json"))
if not reports:
    print("No test reports found")
    exit(1)

latest_report = max(reports, key=lambda p: p.stat().st_mtime)
print(f"Re-validating: {latest_report}\n")

with open(latest_report, 'r', encoding='utf-8') as f:
    results = json.load(f)

print("="*80)
print("重新验证测试结果")
print("="*80)

for i, result in enumerate(results, 1):
    # Re-validate
    new_validation = validate_expectations(
        result['agent_response'],
        result['expectations']
    )
    result['validation'] = new_validation
    result['success'] = all(new_validation.values())

    print(f"\n场景 {i}: {result['scenario']}")
    print(f"  状态: {'✅ 通过' if result['success'] else '❌ 失败'}")
    print(f"  验证:")
    for check, passed in new_validation.items():
        status = "✓" if passed else "✗"
        print(f"    {status} {check}")

# Summary
print(f"\n{'='*80}")
print("重新验证后的总结")
print(f"{'='*80}")

total = len(results)
passed = sum(1 for r in results if r['success'])
failed = total - passed

print(f"\n总场景数: {total}")
print(f"通过: {passed} ({passed/total*100:.1f}%)")
print(f"失败: {failed} ({failed/total*100:.1f}%)")

# Detailed analysis
print(f"\n详细分析:")

# Timeout analysis
timeout_scenarios = [r for r in results if '超时' in r['agent_response'].get('message', '')]
print(f"\n1. 超时场景: {len(timeout_scenarios)}/{total}")
for r in timeout_scenarios:
    print(f"   - {r['scenario']}")
    print(f"     响应时间: {r['response_time']}秒")
    has_sql = bool(r['agent_response'].get('sql'))
    has_data = bool(r['agent_response'].get('data_table'))
    print(f"     生成SQL: {'是' if has_sql else '否'}, 返回数据: {'是' if has_data else '否'}")

# SQL generation
sql_scenarios = [r for r in results if r['agent_response'].get('sql')]
print(f"\n2. 生成SQL: {len(sql_scenarios)}/{total}")

# Data return
data_scenarios = [r for r in results if r['agent_response'].get('data_table')]
print(f"\n3. 返回数据: {len(data_scenarios)}/{total}")

# Performance
response_times = [r['response_time'] for r in results if r['response_time'] > 0]
print(f"\n4. 性能统计:")
print(f"   平均响应时间: {sum(response_times)/len(response_times):.2f}秒")
print(f"   最快: {min(response_times):.2f}秒")
print(f"   最慢: {max(response_times):.2f}秒")

# Save updated report
updated_report = latest_report.stem + "_revalidated.json"
with open(updated_report, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
print(f"\n更新后的报告已保存到: {updated_report}")
