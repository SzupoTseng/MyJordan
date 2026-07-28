"""紅旗清單與自動偵測(第 3、11 章)。

【WHY 這個模組不做任何判斷,只做提醒】
所有紅旗的正確處置都是同一件事:**就醫**。程式不應該、也沒有能力
去判斷「這個算不算嚴重」。它唯一的價值是:當記錄裡出現某些型態時,
把清單推到家長面前——因為住在其中的人,最容易對緩慢的變化失去敏感度。
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .schemas import DailyRecord


@dataclass(frozen=True)
class RedFlag:
    key: str
    text: str
    action: str


# 【WHY 這些字串要與書稿一字不差】
# scripts/check_assets.py 會拿每一條到書稿裡找。措辭不同就會失敗——
# 這是刻意的:讀者在書上看到的那一句,和工具印出來的那一句,必須是同一句。
# 否則他會以為那是兩件不同的事,或者懷疑自己記錯了。
RED_FLAGS: tuple[RedFlag, ...] = (
    RedFlag("regression", "技能倒退：原本會的忽然不會了", "當天就醫"),
    RedFlag("seizure_pattern", "發作型態改變、頻率增加", "當天就醫"),
    RedFlag("status", "單次發作超過 5 分鐘", "叫救護車"),
    RedFlag("drowsy", "白天異常嗜睡、叫不太醒", "當天就醫"),
    RedFlag("mood", "情緒劇變且找不到環境原因", "當天就醫"),
    RedFlag("neuro", "新出現的步態不穩、手抖", "當天就醫"),
    RedFlag("rash", "皮膚紅疹", "立即聯繫醫師"),
    RedFlag("bleeding", "不明原因的瘀青", "立即聯繫醫師"),
    RedFlag("gi", "持續嘔吐、食慾全失", "立即聯繫醫師"),
    RedFlag("bowel", "超過 3–4 天完全未排便", "就醫"),
)

NEVER_DO = (
    "不要自行停藥、調藥或改變劑量",
    "不要長時間完全不進食",
    "不要自行執行生酮或蛋白質限制",
    "不要在未經醫師確認下加入補充劑",
)


@dataclass(frozen=True)
class Signal:
    """從記錄中偵測到、值得回頭看一眼的型態。**不是診斷。**"""

    key: str
    message: str


def scan(records: Iterable[DailyRecord]) -> list[Signal]:
    """掃描記錄,找出值得注意的型態。"""
    items = sorted(records, key=lambda r: r.date)
    signals: list[Signal] = []
    if len(items) < 7:
        return signals

    recent = items[-7:]
    earlier = items[:-7]

    # 【型態一】情緒回復時間明顯惡化
    recent_rec = [r.emotion_recovery_seconds for r in recent if r.emotion_recovery_seconds is not None]
    earlier_rec = [r.emotion_recovery_seconds for r in earlier if r.emotion_recovery_seconds is not None]
    if len(recent_rec) >= 3 and len(earlier_rec) >= 3:
        recent_avg = sum(recent_rec) / len(recent_rec)
        earlier_avg = sum(earlier_rec) / len(earlier_rec)
        if earlier_avg > 0 and recent_avg > earlier_avg * 1.5:
            signals.append(Signal(
                "emotion_worse",
                f"情緒回復時間近七天明顯拉長（{earlier_avg:.0f} → {recent_avg:.0f} 秒）。"
                f"先查地基（睡眠、身體、用藥、環境變動），再檢討方法。",
            ))

    # 【型態二】獨立完成率下滑
    recent_rate = _rate(recent)
    earlier_rate = _rate(earlier)
    if recent_rate is not None and earlier_rate is not None and recent_rate < earlier_rate - 0.2:
        signals.append(Signal(
            "independence_drop",
            f"獨立完成率下滑（{earlier_rate:.2f} → {recent_rate:.2f}）。"
            f"若同時出現『原本會的不會了』，那是技能倒退——當天就醫。",
        ))

    # 【型態三】睡眠不足
    low = [r for r in recent if r.sleep_hours is not None and r.sleep_hours < 7]
    if len(low) >= 3:
        signals.append(Signal(
            "sleep_debt",
            f"近七天有 {len(low)} 天睡不足 7 小時。睡眠是 C1 的地基（第 11 章），"
            f"這段期間的訓練表現不宜當作能力判斷的依據。",
        ))

    return signals


def _rate(records: list[DailyRecord]) -> float | None:
    total = sum(r.tasks_total for r in records)
    if total == 0:
        return None
    return sum(r.tasks_independent for r in records) / total
