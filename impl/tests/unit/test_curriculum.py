from __future__ import annotations

import pytest

from railway_core import curriculum


def test_ten_materials() -> None:
    assert len(curriculum.all_materials()) == 10
    assert [m.code for m in curriculum.all_materials()] == [f"M{i:02d}" for i in range(1, 11)]


def test_every_material_has_valid_dimension_and_chapter() -> None:
    for material in curriculum.all_materials():
        assert material.dimension in curriculum.DIMENSIONS
        assert 21 <= material.chapter <= 27


def test_get_material_normalizes() -> None:
    assert curriculum.get_material(" m04 ").name == "付錢大作戰"


def test_get_material_unknown() -> None:
    with pytest.raises(KeyError):
        curriculum.get_material("M99")


@pytest.mark.parametrize("code", [f"M{i:02d}" for i in range(1, 10)])
def test_generate_all_drillable(code: str) -> None:
    questions = curriculum.generate(code, count=3, seed=1)
    assert len(questions) == 3
    for question in questions:
        assert question.material == code
        assert question.prompt.strip()
        assert question.answer.strip()


def test_m10_has_no_drill() -> None:
    """M10 是流程不是題庫;產生題目會讓家長誤以為它是紙上作業。"""
    with pytest.raises(ValueError, match="第 26 章"):
        curriculum.generate("M10", count=1)


def test_seed_is_reproducible() -> None:
    a = curriculum.generate("M01", count=5, seed=42)
    b = curriculum.generate("M01", count=5, seed=42)
    assert [q.prompt for q in a] == [q.prompt for q in b]


def test_different_seed_differs() -> None:
    a = curriculum.generate("M08", count=6, seed=1)
    b = curriculum.generate("M08", count=6, seed=2)
    assert [q.prompt for q in a] != [q.prompt for q in b]


def test_role_appears_in_prompt() -> None:
    questions = curriculum.generate("M04", count=1, seed=3, role="站長")
    assert "站長" in questions[0].prompt


@pytest.mark.parametrize("count", [0, -1, 31])
def test_generate_rejects_bad_count(count: int) -> None:
    with pytest.raises(ValueError):
        curriculum.generate("M01", count=count)


def test_count_cap_mentions_time_limit() -> None:
    """上限的理由要寫在錯誤訊息裡——第 21 章:每次不超過 15 分鐘。"""
    with pytest.raises(ValueError, match="15 分鐘"):
        curriculum.generate("M01", count=99)


def test_m04_answer_is_a_sufficient_note() -> None:
    """M04 的答案必須是「足夠支付」的面額,不能比價格小。"""
    for question in curriculum.generate("M04", count=10, seed=5):
        price = int(question.prompt.split("門票要 ")[1].split(" 元")[0])
        answer = int(question.answer.split(" ")[0])
        assert answer >= price


def test_m06_answer_says_less() -> None:
    for question in curriculum.generate("M06", count=6, seed=11):
        assert "變小" in question.answer or "變少" in question.answer


def test_m07_change_is_positive() -> None:
    for question in curriculum.generate("M07", count=8, seed=13):
        change = int(question.answer.split("左手等著拿 ")[1].split(" 元")[0])
        assert change > 0
