"""T01 骨架验证测试 - 验证 DDD 分层结构与 FastAPI 应用可创建。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_app_can_be_created() -> None:
    """FastAPI 应用实例可成功创建。"""
    app = create_app()
    assert app.title is not None
    assert app.version == "0.1.0"


def test_health_endpoint() -> None:
    """/health 接口返回 200 与 ok 状态。"""
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_live_endpoint() -> None:
    """/health/live 接口返回 200。"""
    app = create_app()
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_trace_id_injected() -> None:
    """响应头包含 X-Trace-ID。"""
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert "X-Trace-ID" in response.headers


def test_domain_shared_imports() -> None:
    """DDD 共享内核基类可正常导入。"""
    from app.domain.shared import (
        AggregateRoot,
        DomainEvent,
        Entity,
        EntityId,
        Repository,
        ValueObject,
    )

    assert AggregateRoot is not None
    assert DomainEvent is not None
    assert Entity is not None
    assert EntityId is not None
    assert Repository is not None
    assert ValueObject is not None


def test_error_code_prefix() -> None:
    """所有错误码以 EITP_MT_ 前缀。"""
    from app.interfaces.middleware.error_handler import ErrorCode

    for code in ErrorCode:
        assert code.value.startswith("EITP_MT_"), f"错误码 {code} 缺少 EITP_MT_ 前缀"