from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from railway_core import behavior
from railway_core.schemas import ValidationError


def make_abc(**kwargs: object) -> behavior.AbcRecord:
    base: dict[str, object] = {
        "date": dt.date(2026, 3, 2),
        "time": "16:20",
        "antecedent": "剛被要求收玩具",
        "behavior": "重複說火車 6 次、音量提高",
        "consequence": "我幫他收了玩具",
        "hypothesis": "escape",
    }
    base.update(kwargs)
    return behavior.AbcRecord(**base)  # type: ignore[arg-type]


def test_four_functions_only() -> None:
    assert set(behavior.FUNCTIONS) == {"attention", "escape", "tangible", "sensory"}
    assert set(behavior.STRATEGY) == set(behavior.FUNCTIONS)


@pytest.mark.parametrize("field", ["antecedent", "behavior", "consequence"])
def test_abc_fields_required(field: str) -> None:
    with pytest.raises(ValidationError):
        make_abc(**{field: "  "})


@pytest.mark.parametrize("vague", ["不知道", "沒有原因", "突然就", "無", "？"])
def test_vague_antecedent_rejected(vague: str) -> None:
    """「不知道」幾乎總是代表「當時沒看到」，留著它記錄就廢了。"""
    with pytest.raises(ValidationError, match="等於沒填"):
        make_abc(antecedent=vague)


@pytest.mark.parametrize("bad_time", ["16.20", "25:00", "16:70", "1620", ""])
def test_time_format(bad_time: str) -> None:
    with pytest.raises(ValidationError, match="HH:MM"):
        make_abc(time=bad_time)


def test_unknown_function_rejected() -> None:
    with pytest.raises(ValidationError):
        make_abc(hypothesis="revenge")


def test_duration_range() -> None:
    with pytest.raises(ValidationError):
        make_abc(duration_min=999)


def test_roundtrip() -> None:
    record = make_abc(duration_min=4, setting="家")
    assert behavior.AbcRecord.from_dict(record.to_dict()) == record


def test_from_dict_rejects_unknown_and_missing_date() -> None:
    with pytest.raises(ValidationError, match="未知欄位"):
        behavior.AbcRecord.from_dict({**make_abc().to_dict(), "school": "某國中"})
    with pytest.raises(ValidationError, match="date"):
        behavior.AbcRecord.from_dict({"time": "10:00"})


def test_summary_needs_ten_records() -> None:
    """門檻寫死 10（第 35 章的規格：連續兩週、至少 10 筆）。

    刻意不用 MIN_RECORDS_FOR_HYPOTHESIS ± 1 來構造測資——用常數自己測那個常數，
    等於什麼都沒測。這個洞是變異測試抓出來的。
    """
    assert behavior.MIN_RECORDS_FOR_HYPOTHESIS == 10
    assert behavior.summarize_functions([make_abc() for _ in range(9)]).enough_data is False
    summary = behavior.summarize_functions([make_abc() for _ in range(10)])
    assert summary.enough_data is True
    assert summary.top == "escape"
    assert summary.top_label == "逃避／迴避"


def test_summary_without_hypothesis() -> None:
    summary = behavior.summarize_functions([make_abc(hypothesis="") for _ in range(12)])
    assert summary.top is None
    assert summary.top_label == "（尚無假設）"


def test_hypothesis_sentence_uses_escape_verb() -> None:
    assert "以逃避" in behavior.hypothesis_sentence("A", "B", "escape")
    assert "以獲得" in behavior.hypothesis_sentence("A", "B", "attention")


def test_hypothesis_sentence_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        behavior.hypothesis_sentence("A", "B", "nope")


def test_strategy_for_sensory_warns_tokens_are_useless() -> None:
    """感官功能最重要的一句話：代幣與處罰無效。它必須出現在「不該做」裡。"""
    _, dont = behavior.strategy_for("sensory")
    assert any("無效" in item for item in dont)


def test_strategy_for_escape_keeps_task() -> None:
    do, dont = behavior.strategy_for("escape")
    assert any("任務仍要完成" in item for item in do)
    assert any("鬧就能逃" in item for item in dont)


def test_strategy_unknown() -> None:
    with pytest.raises(ValidationError):
        behavior.strategy_for("nope")


def test_store_roundtrip_and_sorting(tmp_path: Path) -> None:
    store = behavior.AbcStore(tmp_path / "abc.jsonl")
    assert store.all() == []
    store.append(make_abc(time="18:00"))
    store.append(make_abc(time="09:00"))
    store.append(make_abc(date=dt.date(2026, 3, 1), time="23:00"))
    ordered = [(r.date, r.time) for r in store.all()]
    assert ordered == sorted(ordered)
