"""PR3 — EventImportanceService prompt 라인에 AR 텍스트 주입 검증."""
from datetime import date

from app.domains.history_agent.application.response.timeline_response import TimelineEvent
from app.domains.history_agent.application.service.event_importance_service import (
    _build_line,
    _build_line_v2,
    _ar_suffix,
)
from app.infrastructure.config.settings import get_settings


def _event(**overrides) -> TimelineEvent:
    base = dict(
        title="Test",
        date=date(2026, 3, 15),
        category="ANNOUNCEMENT",
        type="CRISIS",
        detail="Sample detail text",
    )
    base.update(overrides)
    return TimelineEvent(**base)


def test_ar_suffix_empty_when_status_not_ok():
    e = _event(abnormal_return_5d=3.5, ar_status="INSUFFICIENT_DATA")
    assert _ar_suffix(e) == ""


def test_ar_suffix_empty_when_ar_value_missing():
    e = _event(abnormal_return_5d=None, ar_status="OK")
    assert _ar_suffix(e) == ""


def test_ar_suffix_format_for_ok_status():
    e = _event(abnormal_return_5d=3.21, ar_status="OK")
    assert _ar_suffix(e) == " ar_5d=+3.21%"


def test_ar_suffix_format_for_negative_ar():
    e = _event(abnormal_return_5d=-2.50, ar_status="OK")
    assert _ar_suffix(e) == " ar_5d=-2.50%"


def test_build_line_includes_ar_when_present():
    e = _event(abnormal_return_5d=3.21, ar_status="OK")
    line = _build_line(0, e)
    assert "ar_5d=+3.21%" in line
    assert "type=CRISIS" in line


def test_build_line_v2_includes_ar_when_present():
    e = _event(abnormal_return_5d=-1.5, ar_status="OK")
    line = _build_line_v2(0, e)
    assert "ar_5d=-1.50%" in line
    assert "type=CRISIS" in line


def test_build_line_no_ar_text_when_missing():
    e = _event()
    line = _build_line(0, e)
    assert "ar_5d=" not in line


def test_flag_disabled_skips_injection(monkeypatch):
    """event_impact_in_importance_prompt=False 면 AR 텍스트 미주입."""
    e = _event(abnormal_return_5d=3.0, ar_status="OK")

    fake_settings = get_settings()

    class _FakeSettings:
        event_impact_in_importance_prompt = False

    monkeypatch.setattr(
        "app.domains.history_agent.application.service.event_importance_service.get_settings",
        lambda: _FakeSettings(),
    )
    line = _build_line(0, e)
    assert "ar_5d=" not in line
    # cleanup not needed; monkeypatch auto-reverts
    _ = fake_settings  # silence linter
