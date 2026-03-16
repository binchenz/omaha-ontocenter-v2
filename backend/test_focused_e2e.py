"""
Focused E2E Test - Only scenarios with available data
"""
import time
import json
from datetime import datetime
from app.database import SessionLocal
from app.services.chat import ChatService
from app.models.user import User
from app.models.project import Project
from app.models.chat_session import ChatSession


class FocusedE2ETest:
    def __init__(self, project_id: int, user_id: int):
        self.project_id = project_id
        self.user_id = user_id
        self.db = SessionLocal()
        self.chat_service = ChatService(project_id=self.project_id, db=self.db)
        self.results = []

    def __del__(self):
        self.db.close()

    def log(self, message: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def test_scenario(self, name: str, question: str, expectations: dict):
        """Test a single scenario"""
        self.log(f"\n{'='*80}")
        self.log(f"测试场景: {name}")
        self.log(f"用户问题: {question}")
        self.log(f"{'='*80}")

        result = {
            "scenario": name,
            "question": question,
            "expectations": expectations,
            "success": False,
            "response_time": 0,
            "agent_response": None,
            "sql_queries": [],
            "errors": [],
            "validation": {}
        }

        try:
            start_time = time.time()

            # Get project config
            project = self.db.query(Project).filter(Project.id == self.project_id).first()
            if not project or not project.omaha_config:
                raise Exception(f"Project {self.project_id} not found or has no config")

            # Create or get chat session
            session = self.db.query(ChatSession).filter(
                ChatSession.project_id == self.project_id,
                ChatSession.user_id == self.user_id
            ).first()

            if not session:
                session = ChatSession(
                    project_id=self.project_id,
                    user_id=self.user_id,
                    title=f"Focused E2E Test {datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                self.db.add(session)
                self.db.commit()
                self.db.refresh(session)

            # Call ChatService
            response = self.chat_service.send_message(
                session_id=session.id,
                user_message=question,
                config_yaml=project.omaha_config,
                llm_provider="deepseek"
            )

            end_time = time.time()
            result["response_time"] = round(end_time - start_time, 2)
            result["agent_response"] = response

            self.log(f"✓ 响应时间: {result['response_time']}秒")
            self.log(f"✓ Agent 回复: {response.get('message', 'N/A')[:150]}...")

            # Extract SQL queries
            sql = response.get("sql")
            if sql:
                result["sql_queries"].append(sql)
                self.log(f"✓ SQL: {sql[:100]}...")

            # Check data returned
            data_table = response.get("data_table", [])
            if data_table:
                self.log(f"✓ 返回数据: {len(data_table)} 行")

            # Validate expectations
            result["validation"] = self.validate_expectations(response, expectations)
            result["success"] = all(result["validation"].values())

            if result["success"]:
                self.log(f"✅ 场景通过")
            else:
                self.log(f"❌ 场景失败")
                for check, passed in result["validation"].items():
                    if not passed:
                        self.log(f"  - {check}: 未通过")

        except Exception as e:
            result["errors"].append(str(e))
            self.log(f"❌ 错误: {str(e)}")

        self.results.append(result)
        return result

    def validate_expectations(self, response: dict, expectations: dict) -> dict:
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

        # Check if results were returned
        if "returns_results" in expectations:
            data_table = response.get("data_table", [])
            validation["returns_results"] = bool(data_table and len(data_table) > 0)

        # Check if specific keywords are in SQL
        if "sql_contains" in expectations:
            sql = response.get("sql", "").lower()
            keywords = expectations["sql_contains"]
            validation["sql_contains"] = all(kw.lower() in sql for kw in keywords)

        return validation

    def run_focused_tests(self):
        """Run focused test scenarios (only with available data)"""
        self.log("\n" + "="*80)
        self.log("开始聚焦测试（仅测试数据存在的场景）")
        self.log("="*80)

        # Scenario 1: 简单查询
        self.test_scenario(
            name="场景1：简单查询",
            question="列出所有商品的名称和价格",
            expectations={
                "understands_query": True,
                "generates_sql": True,
                "returns_results": True
            }
        )

        # Scenario 2: 按城市筛选
        self.test_scenario(
            name="场景2：按城市筛选",
            question="深圳有哪些商品在售？",
            expectations={
                "understands_query": True,
                "generates_sql": True,
                "returns_results": True,
                "sql_contains": ["city", "深圳"]
            }
        )

        # Scenario 3: 价格排序
        self.test_scenario(
            name="场景3：价格排序",
            question="价格最高的10个商品是什么？",
            expectations={
                "understands_query": True,
                "generates_sql": True,
                "returns_results": True,
                "sql_contains": ["order by", "ppy_price"]
            }
        )

        # Scenario 4: 成本分析
        self.test_scenario(
            name="场景4：成本分析",
            question="成本超过30元的商品有哪些？",
            expectations={
                "understands_query": True,
                "generates_sql": True,
                "returns_results": True,
                "sql_contains": ["ppy_current_cost", "30"]
            }
        )

        # Scenario 5: 品类统计
        self.test_scenario(
            name="场景5：品类统计",
            question="每个品类有多少商品？",
            expectations={
                "understands_query": True,
                "generates_sql": True,
                "returns_results": True,
                "sql_contains": ["group by", "product_type_first_level"]
            }
        )

        # Scenario 6: 毛利率计算（挑战）
        self.test_scenario(
            name="场景6：毛利率计算",
            question="计算每个商品的毛利率，显示毛利率低于15%的商品",
            expectations={
                "understands_query": True,
                "generates_sql": True,
                "returns_results": True
            }
        )

        self.generate_report()

    def generate_report(self):
        """Generate test report"""
        self.log("\n" + "="*80)
        self.log("聚焦测试报告")
        self.log("="*80)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed

        self.log(f"\n总测试场景: {total}")
        self.log(f"通过: {passed} ({passed/total*100:.1f}%)")
        self.log(f"失败: {failed} ({failed/total*100:.1f}%)")

        # Performance statistics
        response_times = [r["response_time"] for r in self.results if r["response_time"] > 0]
        if response_times:
            self.log(f"\n性能统计:")
            self.log(f"  平均响应时间: {sum(response_times)/len(response_times):.2f}秒")
            self.log(f"  最快响应: {min(response_times):.2f}秒")
            self.log(f"  最慢响应: {max(response_times):.2f}秒")

        # Detailed results
        self.log(f"\n详细结果:")
        for i, result in enumerate(self.results, 1):
            status = "✅" if result["success"] else "❌"
            self.log(f"\n{i}. {status} {result['scenario']}")
            self.log(f"   问题: {result['question']}")
            self.log(f"   响应时间: {result['response_time']}秒")
            if result["sql_queries"]:
                self.log(f"   SQL: {result['sql_queries'][0][:80]}...")
            if result["errors"]:
                self.log(f"   错误: {result['errors']}")
            if not result["success"]:
                failed_checks = [k for k, v in result['validation'].items() if not v]
                self.log(f"   验证失败: {failed_checks}")

        # Save detailed report to file
        report_file = f"focused_e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        self.log(f"\n详细报告已保存到: {report_file}")


if __name__ == "__main__":
    runner = FocusedE2ETest(project_id=1, user_id=1)
    runner.run_focused_tests()
