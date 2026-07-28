#!/usr/bin/env python3
"""變異測試:把已經修過的缺陷逐一改回去,看測試抓不抓得到。

【WHY 需要這個】
覆蓋率只回答「這一行有沒有被執行過」,不回答「它壞掉時有沒有人發現」。
一份 90% 覆蓋率的測試,完全可能對「把 < 改成 <=」毫無反應。

這裡的每一條變異,都對應一個**在開發本工具時真的犯過、或真的差點犯下**的錯。
把它改回去,測試就必須紅。存活下來的變異 = 一個沒人在看的行為。

用法:
    python3 scripts/mutation_sweep.py

依賴:無(跑的是 impl/selftest.py,純標準庫)。
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMPL = ROOT / "impl"
SRC = IMPL / "src" / "railway_core"


@dataclass(frozen=True)
class Mutation:
    file: str
    original: str
    mutated: str
    描述: str


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        "schemas.py",
        "return all(c.passed for c in self.ability) and bool(self.ability)",
        "return all(c.passed for c in self.ability)",
        "空的標準清單被判為通過（all([]) 是 True 的經典陷阱）",
    ),
    Mutation(
        "schemas.py",
        "        if self.tasks_total == 0:\n            return None",
        "        if self.tasks_total == 0:\n            return 0.0",
        "沒有交辦任務的日子記成 0，會把整週平均拉低",
    ),
    Mutation(
        "schemas.py",
        '_require(len(self.code) <= 4, "code 請用簡短代號(≤4 字),真名請放附錄D 的私人檔")',
        '_require(len(self.code) <= 40, "code 請用簡短代號(≤4 字),真名請放附錄D 的私人檔")',
        "代號長度不設限，真名會被順手填進設定檔",
    ),
    Mutation(
        "schemas.py",
        "_require(self.tasks_independent <= self.tasks_total,",
        "_require(self.tasks_independent >= 0 or True,  # noqa\n                 self.tasks_independent <= self.tasks_total or True,",
        "獨立完成數可以大於交辦總數（不可能的資料被接受）",
    ),
    Mutation(
        "stages.py",
        "        if actual is None:\n            return False",
        "        if actual is None:\n            return True",
        "沒量到的指標被當成通過 —— 附錄C 的頭號反模式",
    ),
    Mutation(
        "stages.py",
        "        if self.window_days < 7:",
        "        if self.window_days < 0:",
        "允許用單日表現當離站標準",
    ),
    Mutation(
        "stages.py",
        "        if not self.domains:",
        "        if False:",
        "允許只在一個場合成立的能力（實際上是零個場合）",
    ),
    Mutation(
        "gate.py",
        "        caregiver_ok=caregiver_flags < 3,",
        "        caregiver_ok=caregiver_flags <= 3,",
        "照顧者自檢剛好 3 項時放行（差一錯誤）",
    ),
    Mutation(
        "gate.py",
        "    if unknown:",
        "    if False:",
        "指標名打錯時靜默忽略 —— 那條標準會永遠不通過而沒人知道",
    ),
    Mutation(
        "tracking.py",
        "        independent_task_rate=(total_independent / total_tasks) if total_tasks else",
        "        independent_task_rate=(statistics.mean(rates) if rates else None) or",
        "用每日比率平均取代總數比，讓「交辦 1 件成功 1 件」的日子權重過高",
    ),
    Mutation(
        "tracking.py",
        "        cutoff = records[-1].date - _timedelta(days - 1)",
        "        cutoff = records[0].date - _timedelta(days - 1)",
        "視窗基準取錯端點，最近 N 天會取到最舊的資料",
    ),
    Mutation(
        "tracking.py",
        "        records.sort(key=lambda r: r.date)",
        "        pass",
        "不依日期排序，補登的記錄會讓趨勢計算錯亂",
    ),
    Mutation(
        "curriculum.py",
        "    if not material.has_drill:",
        "    if False:",
        "M10（流程，非題庫）也產生題目，家長會以為它是紙上作業",
    ),
    Mutation(
        "curriculum.py",
        "    if count > 30:",
        "    if count > 100000:",
        "題目數量不設上限，違反「每次不超過 15 分鐘」",
    ),
    Mutation(
        "visuals.py",
        "{escape(task)}",
        "{task}",
        "任務名稱不做跳脫，含 < > 的字會破壞整張 SVG",
    ),
    Mutation(
        "visuals.py",
        "    if len(tasks) > 5:",
        "    if len(tasks) > 50:",
        "檢核卡格數不設限，現場沒有人用得起來",
    ),
    Mutation(
        "safety.py",
        "    if len(items) < 7:\n        return signals",
        "    if len(items) < 0:\n        return signals",
        "資料不足一週就開始下判斷，會給出雜訊等級的警告",
    ),
    Mutation(
        "safety.py",
        "    if len(low) >= 3:",
        "    if len(low) >= 30:",
        "睡眠不足永遠不會被提醒 —— 而它是 C1 最常見的隱形殺手",
    ),
    Mutation(
        "behavior.py",
        "    if not text:",
        "    if False:",
        "ABC 的 A 或 C 可以留白 —— 沒有前事與後果，行為只是孤立事件",
    ),
    Mutation(
        "behavior.py",
        "    if text in _VAGUE:",
        "    if False:",
        "A 欄填「不知道」被接受 —— 兩週後整份記錄無法判讀",
    ),
    Mutation(
        "behavior.py",
        "MIN_RECORDS_FOR_HYPOTHESIS = 10",
        "MIN_RECORDS_FOR_HYPOTHESIS = 1",
        "一筆記錄就下功能結論 —— 那是最近一次事件的印象，不是型態",
    ),
    Mutation(
        "behavior.py",
        "        if self.hypothesis and self.hypothesis not in FUNCTIONS:",
        "        if False:",
        "功能假設可以填任何字串（例如「他想報復我」），統計就全亂了",
    ),
    Mutation(
        "visuals.py",
        "    if len(steps) > 12:",
        "    if len(steps) > 1200:",
        "工作分析卡步數不設限，現場沒有人邊做邊記得完",
    ),
    Mutation(
        "visuals.py",
        "    if not 7 <= days <= 31:\n        raise ValueError(\"一張表 7–31 天；更長會讓格子小到寫不下\")",
        "    if False:\n        raise ValueError(\"一張表 7–31 天；更長會讓格子小到寫不下\")",
        "每日記錄表天數不設限，格子會小到寫不下（記錄中斷的第一個原因）",
    ),
    Mutation(
        "visuals.py",
        "    if not 4 <= rows <= 20:",
        "    if False:",
        "ABC 表列數不設限，前事與後果寫不下就等於沒記",
    ),
    Mutation(
        "visuals.py",
        "    if not 3 <= len(candidates) <= 8:",
        "    if False:",
        "偏好評估候選不設限，配對次數會爆炸（8 個就有 28 對）",
    ),
)


def run_selftest() -> bool:
    """回傳 True 代表測試通過(對變異而言 = 沒抓到 = 壞消息)。"""
    proc = subprocess.run(
        [sys.executable, "selftest.py"], cwd=IMPL, capture_output=True, text=True
    )
    return proc.returncode == 0


def main() -> int:
    if not run_selftest():
        print("✗ 基準測試就沒過,先把 impl/selftest.py 修綠再跑變異測試")
        return 1

    survived: list[Mutation] = []
    killed = 0

    for i, mutation in enumerate(MUTATIONS, 1):
        path = SRC / mutation.file
        original_text = path.read_text(encoding="utf-8")
        if mutation.original not in original_text:
            print(f"  [{i:02d}] ⚠ 找不到目標片段（程式碼已變動）：{mutation.file} — {mutation.描述}")
            survived.append(mutation)
            continue
        path.write_text(original_text.replace(mutation.original, mutation.mutated, 1),
                        encoding="utf-8")
        try:
            passed = run_selftest()
        finally:
            path.write_text(original_text, encoding="utf-8")

        if passed:
            print(f"  [{i:02d}] ✗ 存活：{mutation.描述}")
            survived.append(mutation)
        else:
            killed += 1
            print(f"  [{i:02d}] ✓ 被抓到：{mutation.描述}")

    total = len(MUTATIONS)
    print(f"\n殺死率：{killed}/{total}（{killed / total:.0%}）")
    if survived:
        print("\n存活的變異代表『這個行為壞掉時沒有人會發現』：")
        for mutation in survived:
            print(f"  · {mutation.file}：{mutation.描述}")
        return 1
    print("✓ 全部變異都被測試抓到")
    return 0


if __name__ == "__main__":
    sys.exit(main())
