"""六大階段的定義與離站標準(第 12、13–18、20 章)。

【WHY 把標準寫死在程式裡,而不是放在設定檔】
這些標準是書的一部分。若放進使用者可改的設定檔,兩件事會同時發生:
① 家長為了「這學期能過」而下修標準(附錄C 的反模式之一);
② 書與工具不同步,而沒有人會發現。
現在它們寫在這裡,並由 scripts/check_assets.py 與書稿對照——
要改標準,就要同時改書。這是刻意增加的摩擦。
"""
from __future__ import annotations

from dataclasses import dataclass

STAGE_ORDER: tuple[str, ...] = ("S1", "S2", "S3", "S4", "S5", "S6")


@dataclass(frozen=True)
class Criterion:
    """一條離站標準。

    四要件(第 20 章):行為(label)、數量(threshold)、時間窗口(window_days)、
    場域(domains)。缺一不可——所以這四個欄位都是必填。
    """

    metric: str
    label: str
    threshold: float
    comparator: str            # ">=" 或 "<="
    unit: str
    window_days: int
    domains: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.comparator not in (">=", "<="):
            raise ValueError(f"comparator 只能是 >= 或 <=,收到 {self.comparator!r}")
        if self.window_days < 7:
            raise ValueError("時間窗口至少 7 天:單日表現不算數(第 20 章)")
        if not self.domains:
            raise ValueError("場域不可為空:只在一個場合成立的能力不算數")

    def target_text(self) -> str:
        return f"{self.comparator} {self.threshold:g} {self.unit}（{self.window_days} 天／{'＋'.join(self.domains)}）"

    def check(self, actual: float | None) -> bool:
        if actual is None:
            return False
        return actual >= self.threshold if self.comparator == ">=" else actual <= self.threshold


@dataclass(frozen=True)
class Stage:
    code: str
    name: str
    school_phase: str
    main_core: str
    criteria: tuple[Criterion, ...]

    def next_code(self) -> str | None:
        idx = STAGE_ORDER.index(self.code)
        return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None


_STAGES: dict[str, Stage] = {
    "S1": Stage(
        code="S1", name="奠基期", school_phase="國三上", main_core="C1",
        criteria=(
            Criterion("emotion_recovery_seconds", "情緒回復時間", 120, "<=", "秒", 14, ("家",)),
            Criterion("independent_task_rate", "看卡無提示完成率", 0.7, ">=", "", 14, ("家",)),
            Criterion("gesture_stop_rate", "手勢制止成功率", 0.8, ">=", "", 14, ("家",)),
        ),
    ),
    "S2": Stage(
        code="S2", name="轉化期", school_phase="國三下", main_core="C2",
        criteria=(
            Criterion("chain_level", "指令鏈級數", 6, ">=", "級", 14, ("家", "學校")),
            Criterion("echo_rate", "覆誦率", 0.7, ">=", "", 14, ("家", "學校")),
            Criterion("money_recognition_rate", "面額辨識正確率", 0.8, ">=", "", 14, ("家", "社區")),
        ),
    ),
    "S3": Stage(
        code="S3", name="職業探索期", school_phase="高職一", main_core="C1+C3",
        criteria=(
            Criterion("anger_events_per_week", "每週生氣次數", 2, "<=", "次", 21, ("學校",)),
            Criterion("tool_types", "可獨立操作的工具種類", 3, ">=", "種", 14, ("家", "學校")),
            Criterion("station_minutes", "崗位穩定時間", 20, ">=", "分", 14, ("學校",)),
            Criterion("scripted_phrases_per_week", "自發使用制式台詞", 3, ">=", "次", 14, ("家", "學校")),
        ),
    ),
    "S4": Stage(
        code="S4", name="職場耐受期", school_phase="高職二", main_core="C1",
        criteria=(
            Criterion("distraction_minutes", "干擾下持續工作", 25, ">=", "分", 14, ("家", "學校")),
            Criterion("quality_rate", "作業合格率", 0.9, ">=", "", 14, ("學校",)),
            Criterion("help_requests_per_week", "疲勞時無提示求助", 2, ">=", "次", 14, ("家", "學校")),
        ),
    ),
    "S5": Stage(
        code="S5", name="實習期", school_phase="高職三上", main_core="C2+C1",
        criteria=(
            Criterion("stranger_instruction_rate", "陌生主管指令執行率", 0.8, ">=", "", 14, ("實習現場",)),
            Criterion("fixation_at_work_events", "工作時段主動提起固著", 0, "<=", "次", 14, ("實習現場",)),
            Criterion("commute_grade", "通勤梯度", 3, ">=", "級", 14, ("社區",)),
            Criterion("safety_rate", "交通安全規範遵守率", 1.0, ">=", "", 14, ("社區",)),
        ),
    ),
    "S6": Stage(
        code="S6", name="轉銜期", school_phase="高職三下～畢業後", main_core="維持與防退化",
        criteria=(
            Criterion("onsite_hours", "每日在崗時數", 4, ">=", "小時", 30, ("機構",)),
            Criterion("adaptation_minutes", "變動後平復時間", 3, "<=", "分", 30, ("機構",)),
            Criterion("handbook_delivered", "交接手冊已交付並說明", 1, ">=", "", 30, ("機構",)),
        ),
    ),
}


def all_stages() -> tuple[Stage, ...]:
    return tuple(_STAGES[code] for code in STAGE_ORDER)


def get_stage(code: str) -> Stage:
    normalized = code.strip().upper()
    if normalized not in _STAGES:
        raise KeyError(f"未知站別 {code!r};可用:{', '.join(STAGE_ORDER)}")
    return _STAGES[normalized]


def metric_names() -> set[str]:
    """所有離站標準用到的指標名。scripts/check_assets.py 用它比對書稿。"""
    return {c.metric for s in all_stages() for c in s.criteria}
