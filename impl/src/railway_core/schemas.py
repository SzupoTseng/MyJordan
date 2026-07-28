"""資料模型:個案設定、每日記錄、判定結果。

【WHY 用 dataclass 而不是 pydantic】
本書的核心主張之一是「不需要買任何東西、不需要裝任何東西」(第 21 章)。
一個家長在深夜想跑一次週報時,不應該先撞上 `pip install` 失敗。
因此整個 railway_core 只用標準庫,驗證邏輯自己寫——多花的那幾十行,
換的是「clone 下來就能跑」。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field, asdict
from typing import Any


class ValidationError(ValueError):
    """資料不合法。刻意獨立成一個型別,讓 CLI 能分辨『使用者輸錯』與『程式壞掉』。"""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValidationError(msg)


def parse_date(value: str) -> _dt.date:
    """接受 YYYY-MM-DD。

    【WHY 不接受多種格式】家長會在不同裝置上輸入,而「03/04」在台灣是三月四日、
    在別的地方是四月三日。一種格式,零歧義。
    """
    try:
        return _dt.date.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - 訊息轉換
        raise ValidationError(f"日期格式必須是 YYYY-MM-DD,收到:{value!r}") from exc


@dataclass(frozen=True)
class Profile:
    """個案設定。

    【WHY 這裡沒有姓名欄位】本書是雙軌設計(附錄D):可識別資訊留在家裡。
    工具鏈只需要一個代號就能運作,因此它連存放真名的欄位都不提供——
    沒有欄位,就不會有人不小心填進去,也不會被同步到任何地方。
    """

    code: str                      # 代號,例如 "J"
    stage: str                     # 目前站別 S1..S6
    fixation_topic: str = "火車"   # 固著主題(用於教材外殼)
    role_title: str = "維修長"     # 角色稱號(第 15 章)
    chain_level: int = 1           # 十六級指令階梯的目前級數

    def __post_init__(self) -> None:
        _require(bool(self.code.strip()), "code 不可為空")
        # 【WHY 限制到 4 個字】不是為了排版,是為了攔截「順手把真名填進來」。
        # 四個字擋不住所有名字(三字姓名仍會通過),但它會讓多數人在打字的當下
        # 停一秒——而真正的防線是 scripts/check_book.py 的去識別化檢查。
        _require(len(self.code) <= 4, "code 請用簡短代號(≤4 字),真名請放附錄D 的私人檔")
        _require(1 <= self.chain_level <= 16, "chain_level 必須在 1..16")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Profile":
        known = {f for f in Profile.__dataclass_fields__}
        unknown = set(data) - known
        _require(not unknown, f"未知欄位:{sorted(unknown)}")
        return Profile(**data)


@dataclass(frozen=True)
class DailyRecord:
    """一天的觀察記錄。

    欄位刻意只有三個核心指標 + 兩個地基欄位:第 1 章的原則是
    「能持續兩年的記錄,才是有用的記錄」。欄位越多,放棄得越快。
    """

    date: _dt.date
    emotion_recovery_seconds: int | None = None   # 情緒回復時間(秒)
    tasks_total: int = 0                          # 當日交辦任務數
    tasks_independent: int = 0                    # 其中無額外提醒完成的數量
    chain_steps_ok: int | None = None             # 當日穩定完成的指令步數
    fixation_talk_minutes: int | None = None      # 固著話題總時長(分)
    fixation_structured: bool | None = None       # 該次敘述是否達「有結構」
    sleep_hours: float | None = None              # 睡眠時數(地基②)
    note: str = ""

    def __post_init__(self) -> None:
        if self.emotion_recovery_seconds is not None:
            _require(0 <= self.emotion_recovery_seconds <= 7200,
                     "emotion_recovery_seconds 應在 0..7200 秒")
        _require(self.tasks_total >= 0, "tasks_total 不可為負")
        _require(self.tasks_independent >= 0, "tasks_independent 不可為負")
        _require(self.tasks_independent <= self.tasks_total,
                 "獨立完成數不可大於交辦總數")
        if self.chain_steps_ok is not None:
            _require(0 <= self.chain_steps_ok <= 10, "chain_steps_ok 應在 0..10")
        if self.sleep_hours is not None:
            _require(0 <= self.sleep_hours <= 24, "sleep_hours 應在 0..24")

    @property
    def independent_rate(self) -> float | None:
        """當日獨立完成率。沒有交辦任務的日子回傳 None,而不是 0。

        【WHY 不回傳 0】週末、生病、請假的日子沒有交辦,若記成 0,
        會把整週的平均拉低,讓家長誤以為退步——而那只是那天沒上學。
        """
        if self.tasks_total == 0:
            return None
        return self.tasks_independent / self.tasks_total

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["date"] = self.date.isoformat()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DailyRecord":
        raw = dict(data)
        known = {f for f in DailyRecord.__dataclass_fields__}
        unknown = set(raw) - known
        _require(not unknown, f"未知欄位:{sorted(unknown)}")
        date_value = raw.pop("date", None)
        _require(isinstance(date_value, str), "記錄必須有 date 欄位(YYYY-MM-DD)")
        assert isinstance(date_value, str)
        return DailyRecord(date=parse_date(date_value), **raw)


@dataclass(frozen=True)
class GateCheck:
    """單一離站標準的檢查結果。"""

    metric: str
    label: str
    target: str
    actual: str
    passed: bool


@dataclass(frozen=True)
class GateResult:
    """三道門的完整判定結果(第 20 章)。"""

    stage: str
    ability: list[GateCheck] = field(default_factory=list)
    foundation_ok: bool = True
    foundation_notes: list[str] = field(default_factory=list)
    caregiver_ok: bool = True
    caregiver_flags: int = 0

    @property
    def ability_ok(self) -> bool:
        return all(c.passed for c in self.ability) and bool(self.ability)

    @property
    def passed(self) -> bool:
        return self.ability_ok and self.foundation_ok and self.caregiver_ok

    @property
    def blocked_by(self) -> list[str]:
        blockers: list[str] = []
        if not self.ability_ok:
            blockers.append("能力門")
        if not self.foundation_ok:
            blockers.append("地基門")
        if not self.caregiver_ok:
            blockers.append("照顧者門")
        return blockers
