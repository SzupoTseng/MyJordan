"""離站判定:三道門(第 20 章)。

【WHY 判定函式不接受「大概」】
每一條標準都必須拿到一個數字。拿不到數字的項目一律判為未通過,
而不是「暫且當作通過」——因為附錄C 的反模式之一,就是
「為了進度而放寬標準」,而放寬最常見的形式，就是把沒量到的東西當成過了。
"""
from __future__ import annotations

from .schemas import GateCheck, GateResult
from .stages import Stage, get_stage
from .tracking import METRICS


def evaluate(
    stage: str | Stage,
    metrics: dict[str, float],
    *,
    foundation_notes: list[str] | None = None,
    caregiver_flags: int = 0,
) -> GateResult:
    """判定是否可以離站。

    參數
    ----
    metrics
        指標名 → 實測值。缺少的指標一律視為未通過。
    foundation_notes
        地基門的紅燈事由（睡眠混亂、剛調藥、剛生病、技能倒退…）。
        非空 = 地基門未通過。
    caregiver_flags
        照顧者自檢勾選的項目數（第 11 章）。≥ 3 = 照顧者門未通過。
    """
    stage_obj = stage if isinstance(stage, Stage) else get_stage(stage)
    notes = list(foundation_notes or [])

    unknown = set(metrics) - set(METRICS)
    if unknown:
        # 【WHY 這裡要炸】拼錯的指標名會被靜默忽略,然後那條標準永遠不通過,
        # 而家長只會覺得孩子過不了關。寧可現在就報錯。
        raise KeyError(f"未登記的指標:{sorted(unknown)}（見 tracking.METRICS）")

    checks: list[GateCheck] = []
    for criterion in stage_obj.criteria:
        actual = metrics.get(criterion.metric)
        checks.append(GateCheck(
            metric=criterion.metric,
            label=criterion.label,
            target=criterion.target_text(),
            actual="（未測量）" if actual is None else f"{actual:g}",
            passed=criterion.check(actual),
        ))

    return GateResult(
        stage=stage_obj.code,
        ability=checks,
        foundation_ok=not notes,
        foundation_notes=notes,
        caregiver_ok=caregiver_flags < 3,
        caregiver_flags=caregiver_flags,
    )


def render(result: GateResult) -> str:
    """把判定結果排版成可以貼進會議紀錄的文字。"""
    stage_obj = get_stage(result.stage)
    lines = [
        f"離站判定　{stage_obj.code} {stage_obj.name}（{stage_obj.school_phase}・主核心 {stage_obj.main_core}）",
        "─" * 60,
        "【門 1】能力門",
    ]
    for check in result.ability:
        mark = "✓" if check.passed else "✗"
        lines.append(f"  {mark} {check.label}：實測 {check.actual}　目標 {check.target}")
    lines.append(f"  → {'PASS' if result.ability_ok else 'FAIL'}")

    lines.append("【門 2】地基門")
    if result.foundation_ok:
        lines.append("  ✓ 五塊地基未亮紅燈")
    else:
        for note in result.foundation_notes:
            lines.append(f"  ✗ {note}")
    lines.append(f"  → {'PASS' if result.foundation_ok else 'FAIL'}")

    lines.append("【門 3】照顧者門")
    lines.append(f"  {'✓' if result.caregiver_ok else '✗'} 自檢勾選 {result.caregiver_flags} 項（門檻 < 3）")
    lines.append(f"  → {'PASS' if result.caregiver_ok else 'FAIL'}")

    lines.append("─" * 60)
    if result.passed:
        nxt = stage_obj.next_code()
        lines.append(f"判定：可進入 {nxt}" if nxt else "判定：已在最後一站，轉為長期維持")
    else:
        lines.append(f"判定：留站（卡在 {'、'.join(result.blocked_by)}）")
        lines.append("留站不是失敗。四年跑完六站是理想值，不是及格線（第 12 章）。")
    return "\n".join(lines)
