#!/usr/bin/env python3
"""驗證書稿與 impl/ 工具包沒有走散。

守住六件真的會出問題的事:
  1. 書中十組教材的編號,與 railway_core.curriculum 的註冊表一致
  2. 書中六站代號,與 railway_core.stages 一致
  3. 離站標準引用的指標名,全部登記在 railway_core.tracking.METRICS
  4. .env.example 涵蓋程式讀取的每個環境變數
  5. 程式裡的紅旗清單,書稿裡查得到(工具有、書沒寫 = 讀者永遠不會知道)
  6. 列印資產的檔名,與 impl/README.md 寫的一致
  7. 附錄A 的情境索引,與第七篇正文的五十景一一對應

最後再跑一次 impl/selftest.py(零依賴煙霧測試)。

用法:python3 scripts/check_assets.py   (回傳非零即 FAIL,可直接掛 CI)
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMPL = ROOT / "impl"
sys.path.insert(0, str(IMPL / "src"))

from railway_core import curriculum, safety, stages, tracking  # noqa: E402
from railway_core import settings as settings_mod  # noqa: E402
from railway_core import visuals  # noqa: E402

failures: list[str] = []


def book_text() -> str:
    """所有書稿(不含建置產物)串起來的全文。"""
    parts = []
    for path in sorted(ROOT.glob("*.md")):
        if path.name.startswith("慢車到站") or path.name in (
                "README.md", "BUILD_STANDARD.md", "CHANGELOG.md"):
            continue
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def check_materials(text: str) -> None:
    """書中出現的 M01..M99 編號,必須都在註冊表裡;註冊表裡的也必須都寫進書。"""
    in_book = set(re.findall(r"\bM\d{2}\b", text))
    in_code = set(curriculum.MATERIALS)
    for code in sorted(in_book - in_code):
        failures.append(f"書中提到教材 {code},但 curriculum 沒有註冊")
    for code in sorted(in_code - in_book):
        failures.append(f"curriculum 註冊了 {code},但書裡沒有寫——讀者不會知道它存在")

    # 章節對應也要一致:註冊表宣稱 M04 在第 23 章,書裡第 23 章就必須提到 M04
    for code, material in curriculum.MATERIALS.items():
        chapter_files = list(ROOT.glob(f"{material.chapter:02d}_*.md"))
        if not chapter_files:
            failures.append(f"{code} 宣稱在第 {material.chapter} 章,但找不到該章檔案")
            continue
        if code not in chapter_files[0].read_text(encoding="utf-8"):
            failures.append(
                f"{code} 宣稱在第 {material.chapter} 章({chapter_files[0].name}),但該章沒提到它"
            )


def check_stages(text: str) -> None:
    for code in stages.STAGE_ORDER:
        if code not in text:
            failures.append(f"stages 定義了 {code},但書裡沒有出現")
    for code in sorted(set(re.findall(r"\bS[1-9]\b", text))):
        if code not in stages.STAGE_ORDER:
            failures.append(f"書中出現站別 {code},但 stages 沒有定義")


def check_metrics() -> None:
    """【WHY】離站標準引用一個沒登記的指標,判定會靜默地永遠不通過,
    而家長只會覺得「孩子一直過不了關」。這是最難查的一種錯。
    """
    missing = stages.metric_names() - tracking.metric_names()
    for name in sorted(missing):
        failures.append(f"離站標準用了未登記的指標 {name}(見 tracking.METRICS)")


def check_env_example() -> None:
    example_path = IMPL / ".env.example"
    if not example_path.exists():
        failures.append("impl/.env.example 不存在")
        return
    example = example_path.read_text(encoding="utf-8")
    for name in settings_mod.ENV_VARS:
        if name not in example:
            failures.append(f".env.example 沒有涵蓋環境變數 {name}")


def check_red_flags(text: str) -> None:
    """程式裡的紅旗,書稿裡要查得到。

    【WHY】工具會提醒,但家長不會只看工具。若某一條紅旗只存在於程式碼,
    那些沒跑過 CLI 的讀者(絕大多數)就永遠不會知道它。
    """
    # 取每條紅旗的關鍵詞(冒號或「，」之前的那一段)當比對依據
    for flag in safety.RED_FLAGS:
        keyword = re.split(r"[：，、（(]", flag.text)[0].strip()
        if keyword and keyword not in text:
            failures.append(f"紅旗「{keyword}」只在程式裡,書稿沒有寫")
    for item in safety.NEVER_DO:
        keyword = re.split(r"[，、（(]", item)[0].replace("不要", "").strip()
        if keyword and keyword not in text:
            failures.append(f"「永遠不要」項目「{keyword}」只在程式裡,書稿沒有寫")


def check_scenario_index() -> None:
    """附錄A 的情境索引,必須與第七篇正文的情境一一對應。

    【WHY】索引是手寫的,而正文有五十景。改了一景的標題卻忘記改索引,
    讀者就會在索引裡找不到他要的那一景——而索引存在的唯一理由,
    就是讓人在最急的時候找得到東西。
    """
    body: dict[int, str] = {}
    for path in sorted(ROOT.glob("4[1-5]_*.md")):
        for m in re.finditer(r"(?m)^## 情境 (\d+)　(.+)$", path.read_text(encoding="utf-8")):
            body[int(m.group(1))] = m.group(2).strip()

    index_path = ROOT / "附錄A_速查索引.md"
    if not index_path.exists():
        failures.append("附錄A 不存在")
        return
    # 【WHY 要先切節】附錄A 裡還有一張「每一章的一句話」表格,格式同樣是
    # 「| 數字 | 文字 |」。不切節就會把章號當成情境編號,產生 40 筆假錯誤——
    # 這個誤判在第一次跑就發生了。
    full = index_path.read_text(encoding="utf-8")
    section = re.split(r"(?m)^## ", full)
    scenario_section = next((s for s in section if s.startswith("七之二")), "")
    if not scenario_section:
        failures.append("附錄A 找不到「五十情境總索引」一節")
        return
    index: dict[int, str] = {}
    for m in re.finditer(r"(?m)^\| (\d+) \| (.+?) \|", scenario_section):
        index[int(m.group(1))] = m.group(2).strip()

    if not body:
        failures.append("找不到第七篇的情境正文")
        return

    for number, title in sorted(body.items()):
        if number not in index:
            failures.append(f"附錄A 的情境索引缺少第 {number} 景「{title}」")
        elif index[number] != title:
            failures.append(
                f"第 {number} 景標題不一致:正文「{title}」／索引「{index[number]}」"
            )
    for number in sorted(set(index) - set(body)):
        failures.append(f"附錄A 索引有第 {number} 景,但正文沒有")


def check_asset_filenames() -> None:
    readme = IMPL / "README.md"
    if not readme.exists():
        failures.append("impl/README.md 不存在")
        return
    content = readme.read_text(encoding="utf-8")
    for name in visuals.ASSET_FILENAMES:
        if name not in content:
            failures.append(f"impl/README.md 沒有列出產出檔案 {name}")


def run_selftest() -> None:
    selftest = IMPL / "selftest.py"
    if not selftest.exists():
        failures.append("impl/selftest.py 不存在")
        return
    proc = subprocess.run(
        [sys.executable, str(selftest)], cwd=IMPL, capture_output=True, text=True
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-12:]
        failures.append("impl/selftest.py 失敗:\n      " + "\n      ".join(tail))


def main() -> int:
    text = book_text()
    check_materials(text)
    check_stages(text)
    check_metrics()
    check_env_example()
    check_red_flags(text)
    check_scenario_index()
    check_asset_filenames()
    run_selftest()

    if failures:
        print(f"\n✗ 資產檢查 FAILED({len(failures)} 項):")
        for item in failures[:30]:
            print(f"    - {item}")
        if len(failures) > 30:
            print(f"    …另有 {len(failures) - 30} 項")
        return 1
    print("✓ 資產檢查全數通過(教材編號、站別、指標名、.env 覆蓋、紅旗、情境索引、列印檔名、selftest)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
