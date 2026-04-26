"""dashboard_router / history_agent_router 의 chart_interval Query alias 회귀 가드.

회귀: 프론트가 `?chartInterval=1D` (camelCase) 를 보내는데 백엔드 Query() 에 alias
가 누락되어 default 값(보통 "1M") 으로 fallback 되던 버그. 결과적으로 모든 차트가
월봉으로 렌더되었다. fix: 모든 chart_interval Query 에 `alias="chartInterval"` 추가.
"""
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient


def _build_test_app() -> FastAPI:
    """실제 라우터와 동일한 alias 패턴을 가진 미니 endpoint 로 동작 검증."""
    app = FastAPI()

    @app.get("/test")
    def endpoint(
        chart_interval: str = Query(
            "1M", alias="chartInterval", description="봉 단위"
        ),
    ):
        return {"received": chart_interval}

    return app


class TestChartIntervalAliasContract:
    """alias 동작 단위 검증 — 프로덕션 라우터와 같은 Query 시그니처."""

    def test_camelcase_query_param_binds(self):
        client = TestClient(_build_test_app())
        assert client.get("/test?chartInterval=1D").json() == {"received": "1D"}
        assert client.get("/test?chartInterval=1W").json() == {"received": "1W"}
        assert client.get("/test?chartInterval=1Y").json() == {"received": "1Y"}

    def test_snake_case_query_param_does_not_bind(self):
        """alias 지정 시 snake_case 는 받아주지 않음 — public API 는 alias 만."""
        client = TestClient(_build_test_app())
        # alias 가 설정되면 python 식별자는 query string 키로 사용되지 않는다.
        # 따라서 ?chart_interval=1D 는 무시되고 default 1M 사용.
        assert client.get("/test?chart_interval=1D").json() == {"received": "1M"}

    def test_no_param_uses_default(self):
        client = TestClient(_build_test_app())
        assert client.get("/test").json() == {"received": "1M"}


def _collect_chart_interval_params(router):
    """FastAPI router 에서 (path, method, query_param_alias) 튜플 수집.

    chart_interval 이라는 python 식별자를 가진 Query 파라미터의 alias 만 모은다.
    """
    items = []
    for route in router.routes:
        dep = getattr(route, "dependant", None)
        if dep is None:
            continue
        for q in dep.query_params:
            if q.name == "chart_interval" or q.alias == "chartInterval":
                items.append((route.path, list(route.methods)[0], q.name, q.alias))
    return items


class TestRouterAliasIntegration:
    """실제 router 의 dependant 트리에서 alias 가 `chartInterval` 로 설정됐는지 검증.

    회귀 방지: alias 가 누락되면 모든 chart_interval 요청이 default fallback 으로 빠진다.
    """

    def test_dashboard_router_all_chart_interval_use_alias(self):
        from app.domains.dashboard.adapter.inbound.api.dashboard_router import router

        params = _collect_chart_interval_params(router)
        assert params, "dashboard_router 에 chart_interval Query 가 하나도 없음"
        for path, method, name, alias in params:
            assert alias == "chartInterval", (
                f"dashboard {method} {path} chart_interval alias 누락 (current={alias!r})"
            )

    def test_history_agent_router_all_chart_interval_use_alias(self):
        from app.domains.history_agent.adapter.inbound.api.history_agent_router import (
            router,
        )

        params = _collect_chart_interval_params(router)
        assert params, "history_agent_router 에 chart_interval Query 가 하나도 없음"
        for path, method, name, alias in params:
            assert alias == "chartInterval", (
                f"history_agent {method} {path} chart_interval alias 누락 (current={alias!r})"
            )
