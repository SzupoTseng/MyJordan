from __future__ import annotations

import datetime as dt

import pytest

from railway_core.schemas import (
    DailyRecord,
    GateCheck,
    GateResult,
    Profile,
    ValidationError,
    parse_date,
)


def test_parse_date_accepts_iso() -> None:
    assert parse_date("2026-03-02") == dt.date(2026, 3, 2)


@pytest.mark.parametrize("bad", ["03/04/2026", "2026-3-2x", "", "今天"])
def test_parse_date_rejects_other_formats(bad: str) -> None:
    with pytest.raises(ValidationError):
        parse_date(bad)


def test_profile_roundtrip() -> None:
    profile = Profile(code="J", stage="S2", chain_level=6)
    assert Profile.from_dict(profile.to_dict()) == profile


def test_profile_rejects_empty_code() -> None:
    with pytest.raises(ValidationError):
        Profile(code="   ", stage="S1")


def test_profile_rejects_long_code() -> None:
    """長 code 通常代表有人把真名填進來了——那正是這條檢查要擋的。"""
    with pytest.raises(ValidationError, match="附錄D"):
        Profile(code="王小明小朋友", stage="S1")


def test_profile_rejects_bad_chain_level() -> None:
    with pytest.raises(ValidationError):
        Profile(code="J", stage="S1", chain_level=17)


def test_profile_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="未知欄位"):
        Profile.from_dict({"code": "J", "stage": "S1", "real_name": "王小明"})


def test_record_independent_rate() -> None:
    record = DailyRecord(date=dt.date(2026, 3, 2), tasks_total=4, tasks_independent=3)
    assert record.independent_rate == pytest.approx(0.75)


def test_record_without_tasks_returns_none_not_zero() -> None:
    """沒有交辦的日子回傳 None——記成 0 會把整週平均拉低(週末、生病、請假)。"""
    record = DailyRecord(date=dt.date(2026, 3, 2))
    assert record.independent_rate is None


def test_record_rejects_independent_over_total() -> None:
    with pytest.raises(ValidationError):
        DailyRecord(date=dt.date(2026, 3, 2), tasks_total=2, tasks_independent=3)


@pytest.mark.parametrize("kwargs", [
    {"emotion_recovery_seconds": -1},
    {"emotion_recovery_seconds": 99999},
    {"chain_steps_ok": 11},
    {"sleep_hours": 25.0},
])
def test_record_range_checks(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DailyRecord(date=dt.date(2026, 3, 2), **kwargs)  # type: ignore[arg-type]


def test_record_roundtrip() -> None:
    record = DailyRecord(date=dt.date(2026, 3, 2), emotion_recovery_seconds=90,
                         tasks_total=3, tasks_independent=2, note="睡得好")
    assert DailyRecord.from_dict(record.to_dict()) == record


def test_record_from_dict_requires_date() -> None:
    with pytest.raises(ValidationError, match="date"):
        DailyRecord.from_dict({"tasks_total": 1})


def test_record_from_dict_rejects_unknown() -> None:
    with pytest.raises(ValidationError, match="未知欄位"):
        DailyRecord.from_dict({"date": "2026-03-02", "school": "某某國中"})


def test_gate_result_blocked_by() -> None:
    result = GateResult(
        stage="S1",
        ability=[GateCheck("m", "指標", "x", "y", False)],
        foundation_ok=False, foundation_notes=["剛調藥"],
        caregiver_ok=False, caregiver_flags=4,
    )
    assert result.passed is False
    assert result.blocked_by == ["能力門", "地基門", "照顧者門"]


def test_gate_result_empty_ability_is_not_pass() -> None:
    """沒有任何標準時不可判定為通過——空集合的 all() 為 True,那是陷阱。"""
    assert GateResult(stage="S1").ability_ok is False
