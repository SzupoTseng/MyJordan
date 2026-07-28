"""railway_core —— 《慢車到站》的教材與追蹤工具包。

設計原則(與書一致):
  1. 零依賴。只用 Python 標準庫,clone 下來就能跑。
  2. 不存可識別資訊。真名、校名、醫院名留在附錄D 的私人檔。
  3. 標準寫死在程式裡,並由 scripts/check_assets.py 與書稿對照——
     要改標準,就要同時改書。
  4. 不做判斷,只做提醒。所有紅旗的處置都是同一件事:就醫。
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "behavior",
    "curriculum",
    "gate",
    "safety",
    "schemas",
    "settings",
    "stages",
    "tracking",
    "visuals",
]
