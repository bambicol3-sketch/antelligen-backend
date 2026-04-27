"""GetAnnouncementsUseCase / GetCorporateEventsUseCase 의 한국 ticker 정규식 검증.

router 가 normalize_yfinance_ticker 후 "005930.KS" 로 호출하므로 suffix 매칭 필수.
이전 정규식 r"^\\d{6}$" 가 매칭 실패하던 bug 회귀 가드.
"""
from app.domains.dashboard.application.usecase.get_announcements_usecase import (
    _is_korean_ticker as _is_korean_ann,
)
from app.domains.dashboard.application.usecase.get_corporate_events_usecase import (
    _is_korean_ticker as _is_korean_corp,
)


def test_announcement_classifier_accepts_kospi_suffix():
    assert _is_korean_ann("005930.KS") is True
    assert _is_korean_ann("066570.KS") is True


def test_announcement_classifier_accepts_kosdaq_suffix():
    assert _is_korean_ann("068270.KQ") is True


def test_announcement_classifier_accepts_raw_six_digits():
    """suffix 없는 raw 6자리도 한국 (router 정규화 전 경로 호환)."""
    assert _is_korean_ann("005930") is True


def test_announcement_classifier_rejects_us_ticker():
    assert _is_korean_ann("AAPL") is False
    assert _is_korean_ann("TSLA") is False


def test_announcement_classifier_rejects_invalid_formats():
    assert _is_korean_ann("00593.KS") is False  # 5자리
    assert _is_korean_ann("0059300.KS") is False  # 7자리
    assert _is_korean_ann("005930.SS") is False  # 잘못된 suffix
    assert _is_korean_ann("^IXIC") is False
    assert _is_korean_ann("") is False


def test_corporate_classifier_accepts_kospi_suffix():
    assert _is_korean_corp("005930.KS") is True


def test_corporate_classifier_accepts_kosdaq_suffix():
    assert _is_korean_corp("068270.KQ") is True


def test_corporate_classifier_rejects_us_ticker():
    assert _is_korean_corp("AAPL") is False


def test_corporate_classifier_rejects_invalid_formats():
    assert _is_korean_corp("00593") is False
    assert _is_korean_corp("005930.XYZ") is False
