from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from railway_core.schemas import DailyRecord
from railway_core.tracking import RecordStore


@pytest.fixture
def store(tmp_path: Path) -> RecordStore:
    return RecordStore(tmp_path / "records.jsonl")


@pytest.fixture
def base_date() -> dt.date:
    return dt.date(2026, 3, 2)


def make_record(day: dt.date, **kwargs: object) -> DailyRecord:
    defaults: dict[str, object] = {
        "emotion_recovery_seconds": 180,
        "tasks_total": 4,
        "tasks_independent": 2,
        "sleep_hours": 8.0,
    }
    defaults.update(kwargs)
    return DailyRecord(date=day, **defaults)  # type: ignore[arg-type]


@pytest.fixture
def filled_store(store: RecordStore, base_date: dt.date) -> RecordStore:
    """14 天的記錄:前 7 天較差,後 7 天較好。"""
    for i in range(7):
        store.append(make_record(base_date + dt.timedelta(days=i),
                                 emotion_recovery_seconds=300,
                                 tasks_total=4, tasks_independent=1))
    for i in range(7, 14):
        store.append(make_record(base_date + dt.timedelta(days=i),
                                 emotion_recovery_seconds=120,
                                 tasks_total=4, tasks_independent=3))
    return store
