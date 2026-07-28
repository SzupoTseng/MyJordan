"""指標定義、記錄儲存與週報(第 1、20 章)。

【WHY 記錄用 JSONL 而不是資料庫或試算表】
① 一行一天,任何文字編輯器都能開、都能修;
② append-only,不會因為一次誤操作洗掉兩年的紀錄;
③ 出事的時候(換電腦、程式壞掉),用 grep 就能救回來。
家庭的資料保存期是十年以上,格式必須比工具活得久。
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .schemas import DailyRecord, ValidationError

# ─────────────────────────────────────────────────────────────
# 指標登記表
# 【WHY 要有這張表】stages.py 的離站標準會引用指標名。若有人在 stages 裡
# 打錯字(或書上寫了一個程式沒有的指標),判定會靜默地永遠不通過——
# 而家長只會覺得「孩子怎麼一直過不了關」。
# scripts/check_assets.py 會比對:stages 用到的每個指標都必須登記在這裡。
# ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Metric:
    name: str
    label: str
    unit: str
    better: str          # "lower" 或 "higher"
    computed: bool       # True = 可由每日記錄自動算出;False = 需人工觀察填入


_METRICS: tuple[Metric, ...] = (
    Metric("emotion_recovery_seconds", "情緒回復時間", "秒", "lower", True),
    Metric("independent_task_rate", "無提示任務完成率", "", "higher", True),
    Metric("chain_level", "指令鏈級數", "級", "higher", True),
    Metric("fixation_talk_minutes", "固著話題時長", "分", "neutral", True),
    Metric("fixation_structured_ratio", "固著敘述結構化比率", "", "higher", True),
    Metric("sleep_hours", "睡眠時數", "小時", "higher", True),
    Metric("gesture_stop_rate", "手勢制止成功率", "", "higher", False),
    Metric("echo_rate", "覆誦率", "", "higher", False),
    Metric("money_recognition_rate", "面額辨識正確率", "", "higher", False),
    Metric("anger_events_per_week", "每週生氣次數", "次", "lower", False),
    Metric("tool_types", "可獨立操作的工具種類", "種", "higher", False),
    Metric("station_minutes", "崗位穩定時間", "分", "higher", False),
    Metric("scripted_phrases_per_week", "自發使用制式台詞", "次", "higher", False),
    Metric("distraction_minutes", "干擾下持續工作", "分", "higher", False),
    Metric("quality_rate", "作業合格率", "", "higher", False),
    Metric("help_requests_per_week", "疲勞時無提示求助", "次", "higher", False),
    Metric("stranger_instruction_rate", "陌生主管指令執行率", "", "higher", False),
    Metric("fixation_at_work_events", "工作時段主動提起固著", "次", "lower", False),
    Metric("commute_grade", "通勤梯度", "級", "higher", False),
    Metric("safety_rate", "交通安全規範遵守率", "", "higher", False),
    Metric("onsite_hours", "每日在崗時數", "小時", "higher", False),
    Metric("adaptation_minutes", "變動後平復時間", "分", "lower", False),
    Metric("handbook_delivered", "交接手冊已交付並說明", "", "higher", False),
)

METRICS: dict[str, Metric] = {m.name: m for m in _METRICS}


def metric_names() -> set[str]:
    return set(METRICS)


def computed_metric_names() -> set[str]:
    return {m.name for m in _METRICS if m.computed}


# ─────────────────────────────────────────────────────────────
# 記錄儲存
# ─────────────────────────────────────────────────────────────


def append_jsonl(path: Path, payload: dict[str, object]) -> None:
    """附加一行 JSON。append-only,不會因為一次誤操作洗掉兩年的紀錄。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    """讀回所有行。空行略過;壞行報出行號(檔案是手可改的,所以一定會有壞行)。"""
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{path}:{lineno} 不是合法的 JSON") from exc
        rows.append(payload)
    return rows


class RecordStore:
    """每日記錄的 JSONL 檔案。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: DailyRecord) -> None:
        append_jsonl(self.path, record.to_dict())

    def __iter__(self) -> Iterator[DailyRecord]:
        records = [DailyRecord.from_dict(row) for row in read_jsonl(self.path)]
        # 【WHY 要排序】家長會補登前幾天的記錄,檔案順序不等於日期順序。
        records.sort(key=lambda r: r.date)
        return iter(records)

    def all(self) -> list[DailyRecord]:
        return list(iter(self))

    def latest(self, days: int) -> list[DailyRecord]:
        """最近 N 天的記錄(以最後一筆的日期為基準,不是今天)。

        【WHY 不用今天當基準】家長常在週末補登一整週。若用今天算,
        週一跑報表會看到「最近 7 天只有 2 筆」而以為自己漏記了。
        """
        records = self.all()
        if not records:
            return []
        cutoff = records[-1].date - _timedelta(days - 1)
        return [r for r in records if r.date >= cutoff]


def _timedelta(days: int):  # type: ignore[no-untyped-def]
    import datetime as _dt
    return _dt.timedelta(days=days)


# ─────────────────────────────────────────────────────────────
# 週報
# ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Summary:
    days: int
    samples: int
    emotion_recovery_median: float | None
    emotion_recovery_worst: int | None
    independent_task_rate: float | None
    chain_steps_max: int | None
    fixation_talk_median: float | None
    fixation_structured_ratio: float | None
    sleep_median: float | None
    low_sleep_days: int

    def as_metrics(self) -> dict[str, float]:
        """轉成離站判定用的指標字典(只含算得出來的那幾個)。"""
        out: dict[str, float] = {}
        if self.emotion_recovery_median is not None:
            out["emotion_recovery_seconds"] = self.emotion_recovery_median
        if self.independent_task_rate is not None:
            out["independent_task_rate"] = self.independent_task_rate
        if self.fixation_talk_median is not None:
            out["fixation_talk_minutes"] = self.fixation_talk_median
        if self.fixation_structured_ratio is not None:
            out["fixation_structured_ratio"] = self.fixation_structured_ratio
        if self.sleep_median is not None:
            out["sleep_hours"] = self.sleep_median
        return out


def summarize(records: Iterable[DailyRecord]) -> Summary:
    items = list(records)
    recoveries = [r.emotion_recovery_seconds for r in items if r.emotion_recovery_seconds is not None]
    rates = [r.independent_rate for r in items if r.independent_rate is not None]
    chains = [r.chain_steps_ok for r in items if r.chain_steps_ok is not None]
    talks = [r.fixation_talk_minutes for r in items if r.fixation_talk_minutes is not None]
    structured = [r.fixation_structured for r in items if r.fixation_structured is not None]
    sleeps = [r.sleep_hours for r in items if r.sleep_hours is not None]

    total_tasks = sum(r.tasks_total for r in items)
    total_independent = sum(r.tasks_independent for r in items)

    return Summary(
        days=len({r.date for r in items}),
        samples=len(items),
        emotion_recovery_median=statistics.median(recoveries) if recoveries else None,
        emotion_recovery_worst=max(recoveries) if recoveries else None,
        # 【WHY 用總數比,而不是每日比率的平均】
        # 每日比率的平均會讓「只交辦 1 件、成功 1 件」的日子與
        # 「交辦 10 件、成功 7 件」的日子等重。前者其實沒什麼資訊量。
        independent_task_rate=(total_independent / total_tasks) if total_tasks else
        (statistics.mean(rates) if rates else None),
        chain_steps_max=max(chains) if chains else None,
        fixation_talk_median=statistics.median(talks) if talks else None,
        fixation_structured_ratio=(sum(structured) / len(structured)) if structured else None,
        sleep_median=statistics.median(sleeps) if sleeps else None,
        low_sleep_days=sum(1 for s in sleeps if s < 7),
    )


def trend(previous: Summary, current: Summary) -> list[str]:
    """兩段期間的比較。回傳給人看的句子。

    【WHY 只比中位數,不做統計檢定】家庭記錄的樣本數與雜訊,
    撐不起任何顯著性檢定。假裝做得出 p 值,只會給出虛假的確定感。
    """
    lines: list[str] = []
    if previous.emotion_recovery_median is not None and current.emotion_recovery_median is not None:
        delta = current.emotion_recovery_median - previous.emotion_recovery_median
        direction = "縮短" if delta < 0 else "拉長"
        lines.append(f"情緒回復時間{direction} {abs(delta):.0f} 秒"
                     f"（{previous.emotion_recovery_median:.0f} → {current.emotion_recovery_median:.0f}）")
    if previous.independent_task_rate is not None and current.independent_task_rate is not None:
        delta = current.independent_task_rate - previous.independent_task_rate
        direction = "上升" if delta > 0 else "下降"
        lines.append(f"獨立完成率{direction} {abs(delta):.2f}"
                     f"（{previous.independent_task_rate:.2f} → {current.independent_task_rate:.2f}）")
    if current.low_sleep_days >= 3:
        lines.append(f"⚠️ 本期有 {current.low_sleep_days} 天睡不足 7 小時"
                     f"——先看地基②，再檢討方法（第 11 章）")
    if not lines:
        lines.append("資料還不夠比較。先把兩週的基線記滿（第 1 章）。")
    return lines
