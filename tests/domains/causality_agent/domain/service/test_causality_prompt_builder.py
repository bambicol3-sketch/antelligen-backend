"""KR6 — 탐지 유형별 프롬프트 분기 검증."""
from app.domains.causality_agent.domain.service.causality_prompt_builder import (
    build_hypotheses_system_prompt,
)


def test_default_returns_single_bar_prompt():
    """detection_type 미지정/None 은 single_bar fallback."""
    prompt_none = build_hypotheses_system_prompt(None, None)
    prompt_default = build_hypotheses_system_prompt("single_bar", {})
    # 두 응답이 동일 — 미지정 → single_bar.
    assert prompt_none == prompt_default
    assert "단일봉 급등락" in prompt_none


def test_cumulative_prompt_focuses_on_accumulation():
    prompt = build_hypotheses_system_prompt("cumulative_5d_20d", {})
    assert "누적" in prompt
    assert "단일 사건이 아니라" in prompt or "여러 건의 점진적" in prompt


def test_drawdown_start_prompt_targets_trigger():
    prompt = build_hypotheses_system_prompt("drawdown_start", {})
    assert "Drawdown 시작" in prompt
    assert "트리거" in prompt


def test_drawdown_recovery_prompt_targets_rebound():
    prompt = build_hypotheses_system_prompt("drawdown_recovery", {})
    assert "회복" in prompt or "반등" in prompt


def test_trend_prompt_targets_macro_factors():
    prompt = build_hypotheses_system_prompt("trend", {})
    assert "거시 요인" in prompt or "추세" in prompt


def test_volatility_cluster_prompt_separates_main_and_followups():
    prompt = build_hypotheses_system_prompt("volatility_cluster", {})
    assert "클러스터" in prompt
    assert "후속 반응" in prompt or "차익실현" in prompt


def test_unknown_type_falls_back_to_single_bar():
    prompt = build_hypotheses_system_prompt("nonexistent_type", {})
    assert "단일봉 급등락" in prompt


def test_all_prompts_share_common_tool_guide_and_output_format():
    """모든 type 의 프롬프트가 공통 도구 가이드 + 출력 형식 포함."""
    types = [
        "single_bar", "cumulative_5d_20d",
        "drawdown_start", "drawdown_recovery",
        "trend", "volatility_cluster",
    ]
    for t in types:
        prompt = build_hypotheses_system_prompt(t, {})
        # 공통 도구 가이드
        assert "get_price_stats" in prompt
        assert "get_market_comparison" in prompt
        # 공통 출력 형식
        assert "JSON 배열만 출력" in prompt
        assert "DIRECT" in prompt and "MARKET" in prompt
