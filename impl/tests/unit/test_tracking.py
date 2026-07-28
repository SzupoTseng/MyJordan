from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from railway_core import stages, tracking
from railway_core.schemas import DailyRecord, ValidationError
from railway_core.tracking import RecordStore, summarize, trend

from ..conftest import make_record


def test_metrics_cover_all_stage_criteria() -> None:
    assert stages.metric_names() <= tracking.metric_names()


def test_computed_metrics_subset() -> None:
    assert tracking.computed_metric_names() <= tracking.metric_names()


def test_store_roundtrip(store: RecordStore, base_date: dt.date) -> None:
    store.append(make_record(base_date))
    store.append(make_record(base_date + dt.timedelta(days=1)))
    assert len(store.all()) == 2


def test_store_missing_file_is_empty(tmp_path: Path) -> None:
    assert RecordStore(tmp_path / "nope.jsonl").all() == []


def test_store_sorts_by_date(store: RecordStore, base_date: dt.date) -> None:
    """家長會補登前幾天——檔案順序不等於日期順序。"""
    store.append(make_record(base_date + dt.timedelta(days=3)))
    store.append(make_record(base_date))
    dates = [r.date for r in store.all()]
    assert dates == sorted(dates)


def test_store_skips_blank_lines(store: RecordStore, base_date: dt.date) -> None:
    store.append(make_record(base_date))
    with store.path.open("a", encoding="utf-8") as handle:
        handle.write("\n   \n")
    assert len(store.all()) == 1


def test_store_reports_bad_json_with_line_number(store: RecordStore) -> None:
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{壞掉的\n", encoding="utf-8")
    with pytest.raises(ValidationError, match=":1"):
        store.all()


def test_latest_uses_last_record_date_not_today(store: RecordStore) -> None:
    """基準是最後一筆的日期,不是今天——否則週末補登會看起來像漏記。"""
    old = dt.date(2020, 1, 1)
    for i in range(10):
        store.append(make_record(old + dt.timedelta(days=i)))
    assert len(store.latest(3)) == 3


def test_latest_empty(store: RecordStore) -> None:
    assert store.latest(7) == []


def test_summary_uses_totals_not_daily_mean() -> None:
    """交辦 1 件成功 1 件的日子,不應與交辦 10 件成功 7 件的日子等重。"""
    records = [
        DailyRecord(date=dt.date(2026, 3, 1), tasks_total=1, tasks_independent=1),
        DailyRecord(date=dt.date(2026, 3, 2), tasks_total=10, tasks_independent=2),
    ]
    summary = summarize(records)
    assert summary.independent_task_rate == pytest.approx(3 / 11)


def test_summary_empty() -> None:
    summary = summarize([])
    assert summary.samples == 0
    assert summary.emotion_recovery_median is None
    assert summary.as_metrics() == {}


def test_summary_as_metrics_keys_are_registered() -> None:
    records = [make_record(dt.date(2026, 3, 1), fixation_talk_minutes=90,
                           fixation_structured=True)]
    assert set(summarize(records).as_metrics()) <= tracking.metric_names()


def test_summary_counts_low_sleep_days() -> None:
    records = [
        make_record(dt.date(2026, 3, 1), sleep_hours=6.0),
        make_record(dt.date(2026, 3, 2), sleep_hours=6.5),
        make_record(dt.date(2026, 3, 3), sleep_hours=8.0),
    ]
    assert summarize(records).low_sleep_days == 2


def test_trend_reports_improvement(filled_store: RecordStore) -> None:
    records = filled_store.all()
    lines = trend(summarize(records[:7]), summarize(records[7:]))
    assert any("縮短" in line for line in lines)
    assert any("上升" in line for line in lines)


def test_trend_warns_on_sleep_debt() -> None:
    poor = [make_record(dt.date(2026, 3, i + 1), sleep_hours=5.5) for i in range(4)]
    lines = trend(summarize([]), summarize(poor))
    assert any("第 11 章" in line for line in lines)


def test_trend_without_data() -> None:
    assert "第 1 章" in trend(summarize([]), summarize([]))[0]
