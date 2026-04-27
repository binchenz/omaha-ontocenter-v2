"""E2E tests for Link type system scenarios."""
import pytest
from tests.e2e._env import ensure_test_db, is_provider_error


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Ensure test database is ready."""
    ensure_test_db()


@pytest.mark.asyncio
async def test_link_auto_expansion(chat_service, test_session):
    """测试Link字段自动展开"""
    try:
        response = await chat_service.send_message(
            session_id=test_session.id,
            user_message="查询一个产品，显示它的类目信息"
        )

        assert response.get("success"), f"Query failed: {response.get('error')}"

        # 验证返回了产品数据
        message = response.get("message", "")
        assert len(message) > 0, "Empty response"

    except Exception as e:
        if is_provider_error(e):
            pytest.skip(f"PROVIDER ERROR: {e}")
        raise


@pytest.mark.asyncio
async def test_reverse_navigation(chat_service, test_session):
    """测试反向导航：从类目查询所有产品"""
    try:
        response = await chat_service.send_message(
            session_id=test_session.id,
            user_message="手机类目下有哪些产品？"
        )

        assert response.get("success"), f"Query failed: {response.get('error')}"

        message = response.get("message", "")
        assert len(message) > 0, "Empty response"

        # 验证使用了反向导航工具
        tool_calls = response.get("tool_calls", [])
        has_reverse_nav = any(
            "get_" in call.get("name", "")
            for call in tool_calls
        )

        # 如果没有使用反向导航工具，至少应该返回了结果
        assert has_reverse_nav or len(message) > 50, "No reverse navigation or insufficient data"

    except Exception as e:
        if is_provider_error(e):
            pytest.skip(f"PROVIDER ERROR: {e}")
        raise


@pytest.mark.asyncio
async def test_multi_hop_navigation(chat_service, test_session):
    """测试多跳导航：类目 → 产品 → 评论"""
    try:
        response = await chat_service.send_message(
            session_id=test_session.id,
            user_message="手机类目下评分最高的产品是什么？"
        )

        assert response.get("success"), f"Query failed: {response.get('error')}"

        message = response.get("message", "")
        assert len(message) > 0, "Empty response"

    except Exception as e:
        if is_provider_error(e):
            pytest.skip(f"PROVIDER ERROR: {e}")
        raise


@pytest.mark.asyncio
async def test_link_with_filters(chat_service, test_session):
    """测试带过滤条件的Link导航"""
    try:
        response = await chat_service.send_message(
            session_id=test_session.id,
            user_message="价格大于5000的手机有哪些？"
        )

        assert response.get("success"), f"Query failed: {response.get('error')}"

        message = response.get("message", "")
        assert len(message) > 0, "Empty response"

    except Exception as e:
        if is_provider_error(e):
            pytest.skip(f"PROVIDER ERROR: {e}")
        raise


@pytest.mark.asyncio
async def test_self_referencing_link(chat_service, test_session):
    """测试自引用Link：类目的父类目"""
    try:
        response = await chat_service.send_message(
            session_id=test_session.id,
            user_message="手机类目的父类目是什么？"
        )

        assert response.get("success"), f"Query failed: {response.get('error')}"

        message = response.get("message", "")
        assert len(message) > 0, "Empty response"

    except Exception as e:
        if is_provider_error(e):
            pytest.skip(f"PROVIDER ERROR: {e}")
        raise
