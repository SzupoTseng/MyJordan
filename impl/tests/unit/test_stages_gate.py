from __future__ import annotations

import pytest

from railway_core import gate, stages, tracking


def test_all_stages_in_order() -> None:
    codes = [s.code for s in stages.all_stages()]
    assert codes == list(stages.STAGE_ORDER)


def test_get_stage_is_case_insensitive() -> None:
    assert stages.get_stage("s3").name == "職業探索期"


def test_get_stage_unknown() -> None:
    with pytest.raises(KeyError):
        stages.get_stage("S9")


def test_next_code_ends_at_s6() -> None:
    assert stages.get_stage("S5").next_code() == "S6"
    assert stages.get_stage("S6").next_code() is None


def test_every_criterion_metric_is_registered() -> None:
    """離站標準引用的指標,必須都登記在 tracking.METRICS。

    漏掉會讓那條標準永遠不通過,而家長只會覺得「孩子一直過不了關」。
    """
    assert stages.metric_names() <= tracking.metric_names()


def test_every_criterion_has_four_elements() -> None:
    """第 20 章:行為、數量、時間窗口、場域,四者缺一不可。"""
    for stage in stages.all_stages():
        assert stage.criteria, f"{stage.code} 沒有任何離站標準"
        for c in stage.criteria:
            assert c.label
            assert c.window_days >= 7
            assert c.domains


def test_criterion_rejects_bad_comparator() -> None:
    with pytest.raises(ValueError):
        stages.Criterion("m", "標籤", 1, "==", "", 14, ("家",))


def test_criterion_rejects_short_window() -> None:
    with pytest.raises(ValueError, match="單日表現"):
        stages.Criterion("m", "標籤", 1, ">=", "", 3, ("家",))


def test_criterion_rejects_empty_domains() -> None:
    with pytest.raises(ValueError, match="場域"):
        stages.Criterion("m", "標籤", 1, ">=", "", 14, ())


@pytest.mark.parametrize(("comparator", "actual", "expected"), [
    (">=", 0.8, True), (">=", 0.6, False), ("<=", 100, True), ("<=", 200, False),
])
def test_criterion_check(comparator: str, actual: float, expected: bool) -> None:
    threshold = 0.7 if comparator == ">=" else 120
    criterion = stages.Criterion("m", "標籤", threshold, comparator, "", 14, ("家",))
    assert criterion.check(actual) is expected


def test_missing_metric_never_passes() -> None:
    """沒量到的東西不算通過——附錄C 的反模式:為了進度而放寬標準。"""
    criterion = stages.Criterion("m", "標籤", 0, ">=", "", 14, ("家",))
    assert criterion.check(None) is False


def _s1_pass_metrics() -> dict[str, float]:
    return {
        "emotion_recovery_seconds": 110,
        "independent_task_rate": 0.75,
        "gesture_stop_rate": 0.85,
    }


def test_gate_pass() -> None:
    result = gate.evaluate("S1", _s1_pass_metrics())
    assert result.passed
    assert "可進入 S2" in gate.render(result)


def test_gate_fails_on_ability() -> None:
    metrics = _s1_pass_metrics()
    metrics["emotion_recovery_seconds"] = 400
    result = gate.evaluate("S1", metrics)
    assert not result.passed
    assert result.blocked_by == ["能力門"]


def test_gate_fails_on_foundation() -> None:
    result = gate.evaluate("S1", _s1_pass_metrics(), foundation_notes=["近四週睡眠混亂"])
    assert result.blocked_by == ["地基門"]
    assert "近四週睡眠混亂" in gate.render(result)


def test_gate_fails_on_caregiver_at_three_flags() -> None:
    """門檻是「< 3」:剛好 3 項就要留站,不是超過 3 才算。"""
    assert gate.evaluate("S1", _s1_pass_metrics(), caregiver_flags=3).blocked_by == ["照顧者門"]
    assert gate.evaluate("S1", _s1_pass_metrics(), caregiver_flags=2).passed


def test_gate_rejects_unknown_metric() -> None:
    with pytest.raises(KeyError, match="未登記"):
        gate.evaluate("S1", {"emotion_recovry_seconds": 100})


def test_gate_missing_metric_shows_not_measured() -> None:
    text = gate.render(gate.evaluate("S1", {}))
    assert "（未測量）" in text
    assert "留站" in text


def test_render_last_stage_has_no_next() -> None:
    metrics = {
        "onsite_hours": 5, "adaptation_minutes": 2, "handbook_delivered": 1,
    }
    text = gate.render(gate.evaluate("S6", metrics))
    assert "長期維持" in text
