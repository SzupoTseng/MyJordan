"""ABC 記錄與行為功能評估(第 35 章)。

【WHY 這個模組會拒絕不完整的記錄】
ABC 最常見的失敗不是記錯,是**只記 B**——「他今天又鬧了三次」。
沒有前事與後果,行為就只是一個孤立事件,產不出任何結論。
所以這裡的 A 與 C 都是必填,而且會擋掉「不知道」「沒有原因」這類填法:
那通常代表觀察者沒看到,而不是真的沒有前事。
"""
from __future__ import annotations

import datetime as _dt
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .schemas import ValidationError, parse_date
from .tracking import append_jsonl, read_jsonl

# 四大功能。鍵是程式用的代號,值是書上第 35 章的中文名稱。
FUNCTIONS: dict[str, str] = {
    "attention": "獲得注意",
    "escape": "逃避／迴避",
    "tangible": "獲得實體物或活動",
    "sensory": "感官／自動增強",
}

# 每一種功能該做與不該做的事。與第 35 章的對照表一致。
STRATEGY: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "attention": (
        ("行為發生時給予最少反應",
         "在他沒有出現該行為時主動給注意",
         "教他用適當方式要求注意"),
        ("大聲斥責", "長篇說理（那全都是注意）"),
    ),
    "escape": (
        ("降低任務難度、拆步驟（第 36 章）",
         "給選擇權",
         "教他用語言要求休息（FCT）",
         "任務仍要完成，哪怕只完成一步"),
        ("「好啦你不要做了」——那是在教他鬧就能逃",),
    ),
    "tangible": (
        ("明確的規則與時間框",
         "代幣制（第 37 章）",
         "教他用適當方式要求"),
        ("吵到你受不了才給——那是在教他吵久一點",),
    ),
    "sensory": (
        ("提供功能等值的替代感官輸入",
         "調整環境",
         "安排規律的感官活動時段"),
        ("代幣", "處罰", "說理　★ 這三者對感官功能幾乎完全無效"),
    ),
}

# 【WHY 要有這張擋詞表】「不知道」「沒有原因」「突然就」是 A 欄最常見的填法,
# 而它們幾乎總是代表「當時沒看到」。留著它們,兩週後這份記錄會完全無法判讀。
_VAGUE = ("不知道", "沒有原因", "沒原因", "突然就", "無", "不明", "?", "？")


def _check_field(value: str, field: str) -> str:
    text = value.strip()
    if not text:
        raise ValidationError(f"{field} 不可為空：沒有前事與後果，行為只是一個孤立事件")
    if text in _VAGUE:
        raise ValidationError(
            f"{field} 填「{text}」等於沒填。若當時沒看到，請寫下你確實知道的部分"
            f"（例如：在做什麼、誰在場、剛剛被要求了什麼）"
        )
    return text


@dataclass(frozen=True)
class AbcRecord:
    """一筆 ABC 三聯式記錄。"""

    date: _dt.date
    time: str                # HH:MM
    antecedent: str          # A 前事
    behavior: str            # B 行為
    consequence: str         # C 後果：★ 他因此得到了什麼
    duration_min: int | None = None
    setting: str = ""        # 家／學校／社區／機構
    hypothesis: str = ""     # 觀察者當下猜測的功能（可空）

    def __post_init__(self) -> None:
        object.__setattr__(self, "antecedent", _check_field(self.antecedent, "A 前事"))
        object.__setattr__(self, "behavior", _check_field(self.behavior, "B 行為"))
        object.__setattr__(self, "consequence", _check_field(self.consequence, "C 後果"))
        if self.hypothesis and self.hypothesis not in FUNCTIONS:
            raise ValidationError(
                f"功能假設只能是 {'/'.join(FUNCTIONS)} 之一，收到 {self.hypothesis!r}"
            )
        if self.duration_min is not None and not 0 <= self.duration_min <= 480:
            raise ValidationError("duration_min 應在 0..480 分鐘")
        if not _is_hhmm(self.time):
            raise ValidationError(f"time 格式必須是 HH:MM，收到 {self.time!r}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["date"] = self.date.isoformat()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AbcRecord:
        raw = dict(data)
        known = set(AbcRecord.__dataclass_fields__)
        unknown = set(raw) - known
        if unknown:
            raise ValidationError(f"未知欄位：{sorted(unknown)}")
        date_value = raw.pop("date", None)
        if not isinstance(date_value, str):
            raise ValidationError("記錄必須有 date 欄位（YYYY-MM-DD）")
        return AbcRecord(date=parse_date(date_value), **raw)


def _is_hhmm(text: str) -> bool:
    parts = text.split(":")
    if len(parts) != 2:
        return False
    hour, minute = parts
    if not (hour.isdigit() and minute.isdigit()):
        return False
    return 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59


@dataclass(frozen=True)
class FunctionSummary:
    total: int
    counts: dict[str, int]
    top: str | None
    enough_data: bool

    @property
    def top_label(self) -> str:
        return FUNCTIONS[self.top] if self.top else "（尚無假設）"


# 【WHY 門檻是 10】第 35 章要求連續兩週、至少 10 筆。
# 低於這個數量就下結論,得到的通常是最近一次事件的印象,不是型態。
MIN_RECORDS_FOR_HYPOTHESIS = 10


def summarize_functions(records: Iterable[AbcRecord]) -> FunctionSummary:
    items = list(records)
    counts = Counter(r.hypothesis for r in items if r.hypothesis)
    top = counts.most_common(1)[0][0] if counts else None
    return FunctionSummary(
        total=len(items),
        counts=dict(counts),
        top=top,
        enough_data=len(items) >= MIN_RECORDS_FOR_HYPOTHESIS,
    )


def hypothesis_sentence(antecedent: str, behavior: str, function: str) -> str:
    """把功能假設寫成第 35 章的標準句型（可以直接貼進 IEP）。"""
    if function not in FUNCTIONS:
        raise ValidationError(f"未知的功能 {function!r}")
    verb = "逃避" if function == "escape" else "獲得"
    return (f"當「{antecedent}」發生時，他會「{behavior}」，"
            f"以{verb}「{FUNCTIONS[function]}」，因此這個行為持續發生。")


def strategy_for(function: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """回傳 (該做, 不該做)。"""
    if function not in STRATEGY:
        raise ValidationError(f"未知的功能 {function!r}")
    return STRATEGY[function]


class AbcStore:
    """ABC 記錄的 JSONL 檔案（與每日記錄分開存放）。

    【WHY 分開存】ABC 是為了「處理某一個特定行為」而做的短期密集記錄，
    通常兩週就結束；每日記錄則是長達數年的追蹤。混在一起會讓長期趨勢
    被兩週的密集資料淹沒。
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: AbcRecord) -> None:
        append_jsonl(self.path, record.to_dict())

    def all(self) -> list[AbcRecord]:
        records = [AbcRecord.from_dict(row) for row in read_jsonl(self.path)]
        records.sort(key=lambda r: (r.date, r.time))
        return records
