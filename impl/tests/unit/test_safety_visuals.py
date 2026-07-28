from __future__ import annotations

import datetime as dt
import re

import pytest

from railway_core import safety, visuals

from ..conftest import make_record

# ── safety ───────────────────────────────────────────────────


def test_red_flags_have_actions() -> None:
    assert len(safety.RED_FLAGS) >= 8
    for flag in safety.RED_FLAGS:
        assert flag.text and flag.action


def test_never_do_includes_no_self_stop() -> None:
    assert any("停藥" in item for item in safety.NEVER_DO)


def test_scan_needs_a_week_of_data() -> None:
    records = [make_record(dt.date(2026, 3, i + 1)) for i in range(6)]
    assert safety.scan(records) == []


def test_scan_detects_emotion_deterioration() -> None:
    earlier = [make_record(dt.date(2026, 3, i + 1), emotion_recovery_seconds=100)
               for i in range(7)]
    recent = [make_record(dt.date(2026, 3, i + 8), emotion_recovery_seconds=300)
              for i in range(7)]
    keys = {s.key for s in safety.scan(earlier + recent)}
    assert "emotion_worse" in keys


def test_scan_detects_independence_drop_and_mentions_regression() -> None:
    earlier = [make_record(dt.date(2026, 3, i + 1), tasks_total=4, tasks_independent=4)
               for i in range(7)]
    recent = [make_record(dt.date(2026, 3, i + 8), tasks_total=4, tasks_independent=1)
              for i in range(7)]
    signals = {s.key: s.message for s in safety.scan(earlier + recent)}
    assert "independence_drop" in signals
    assert "就醫" in signals["independence_drop"]


def test_scan_detects_sleep_debt() -> None:
    records = [make_record(dt.date(2026, 3, i + 1), sleep_hours=5.0) for i in range(14)]
    assert "sleep_debt" in {s.key for s in safety.scan(records)}


def test_scan_quiet_when_stable() -> None:
    records = [make_record(dt.date(2026, 3, i + 1)) for i in range(14)]
    assert safety.scan(records) == []


# ── visuals ──────────────────────────────────────────────────


def _is_svg(text: str) -> bool:
    return text.startswith("<svg") and text.rstrip().endswith("</svg>")


def test_checklist_card_renders() -> None:
    asset = visuals.checklist_card(["擦黑板", "排桌椅", "倒垃圾"])
    assert _is_svg(asset.content)
    assert asset.filename == "checklist_card.svg"
    assert "擦黑板" in asset.content


def test_checklist_card_rejects_empty() -> None:
    with pytest.raises(ValueError):
        visuals.checklist_card([])


def test_checklist_card_caps_at_five() -> None:
    """第 13 章:三格起步。六格的卡片在現場沒有人用得起來。"""
    with pytest.raises(ValueError, match="第 13 章"):
        visuals.checklist_card(["a", "b", "c", "d", "e", "f"])


def test_checklist_card_escapes_markup() -> None:
    """任務名稱由使用者提供,含 < > & 時不可破壞 SVG。"""
    asset = visuals.checklist_card(["擦 <黑板> & 桌子"])
    assert "&lt;黑板&gt;" in asset.content
    assert "&amp;" in asset.content
    assert _is_svg(asset.content)


def test_token_board_renders_requested_count() -> None:
    asset = visuals.token_board(count=4, topic="火車")
    assert asset.content.count("火車券") == 4


@pytest.mark.parametrize("count", [0, 7])
def test_token_board_range(count: int) -> None:
    with pytest.raises(ValueError):
        visuals.token_board(count=count)


def test_price_cards_render() -> None:
    asset = visuals.price_cards([("區間車", 150), ("自強號", 400)])
    assert "150 元" in asset.content and "400 元" in asset.content


def test_price_cards_reject_empty_and_too_many() -> None:
    with pytest.raises(ValueError):
        visuals.price_cards([])
    with pytest.raises(ValueError):
        visuals.price_cards([("x", 1)] * 9)


def test_timetable_card_render_and_limit() -> None:
    asset = visuals.timetable_card([("13:00", "區間車"), ("13:30", "自強號")])
    assert "13:30" in asset.content
    with pytest.raises(ValueError, match="第 26 章"):
        visuals.timetable_card([("13:00", "x")] * 6)


@pytest.mark.parametrize(("factory", "keyword"), [
    (visuals.daily_log, "三分鐘"),
    (visuals.abc_form, "他因此得到了什麼"),
    (visuals.sleep_log, "夜間發作"),
    (visuals.preference_form, "非物品"),
])
def test_record_forms_carry_the_book_reminder(factory, keyword: str) -> None:
    """記錄表要把書裡的關鍵提醒印在紙上——填表的人不會同時翻書。"""
    assert keyword in factory().content


@pytest.mark.parametrize("bad", [
    lambda: visuals.daily_log(days=40),
    lambda: visuals.daily_log(days=3),
    lambda: visuals.abc_form(rows=100),
    lambda: visuals.abc_form(rows=1),
    lambda: visuals.sleep_log(days=3),
    lambda: visuals.preference_form(["a", "b"]),
    lambda: visuals.preference_form(["a"] * 9),
])
def test_record_form_bounds(bad) -> None:
    with pytest.raises(ValueError):
        bad()


def test_preference_form_lists_every_pair() -> None:
    """6 個候選 → 15 對，一對都不能少（漏了就不是配對評估）。"""
    content = visuals.preference_form(["a", "b", "c", "d"]).content
    assert content.count("　vs　") == 6


def test_all_assets_declare_filenames() -> None:
    """ASSET_FILENAMES 必須涵蓋所有產生器的輸出,scripts/check_assets.py 依賴它。"""
    produced = {
        visuals.checklist_card(["a"]).filename,
        visuals.token_board().filename,
        visuals.price_cards([("a", 1)]).filename,
        visuals.timetable_card([("13:00", "a")]).filename,
        visuals.task_analysis_card(["a"]).filename,
        visuals.daily_log().filename,
        visuals.abc_form().filename,
        visuals.sleep_log().filename,
        visuals.preference_form().filename,
    }
    assert produced == set(visuals.ASSET_FILENAMES)


def test_svg_has_no_external_references() -> None:
    """列印資產必須自足:不得有外部連結(離線可用、也避免追蹤)。"""
    for asset in (visuals.checklist_card(["a"]), visuals.token_board(),
                  visuals.price_cards([("a", 1)]),
                  visuals.timetable_card([("13:00", "a")])):
        # xmlns 的 http://www.w3.org/2000/svg 是命名空間宣告，不是外部資源。
        body = asset.content.replace('xmlns="http://www.w3.org/2000/svg"', "")
        assert not re.search(r'(https?:|xlink:href|<image|<script)', body)
