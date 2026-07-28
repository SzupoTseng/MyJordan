#!/usr/bin/env python3
"""驗證書稿與建置產物的完整性。

守住六件在本書製作過程中真的出過問題的事:
  1. 架構圖引用不得斷連(md 裡寫的 diagrams/*.svg 必須存在)
  2. 繁體書稿不得混入簡體字
  3. 談到藥物、劑量或醫療處置的章節,必須在同一章帶醫療免責框
  4. 主線章節不得出現可識別個資(化名一律 J;真實個案只准出現在附錄D)
  5. 建置產物必須與當前書稿一致(不能忘記重跑 _build.py 就提交)
  6. 內嵌 21 張 SVG 後,HTML 的 id 必須全域唯一(重複會讓 url(#…) 解析到錯的定義)
  7. 情境百景(第七篇)的七段骨架不得缺段,編號不得重複或跳號
  8. 術語表(附錄F)不得列出正文沒有的詞
  9. 「第 N 章」與「附錄 X」的交叉引用必須真的存在

用法:python3 scripts/check_book.py   (回傳非零即 FAIL,可直接掛 CI)
"""
from __future__ import annotations

import collections
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOK_TITLE = "慢車到站"

# 【WHY 這張表對本書特別重要】本書素材是一份簡體 UI 的 AI 對話匯出,原文裡
# 「说 / 阶段 / 训练 / 药物」滿地都是。書稿是一句一句改寫出來的,只要有一句漏改,
# 繁體書裡就躺著一個簡體字——讀者不會回報,他們只會覺得這本書很粗糙。
# 僅收錄「簡體專用、繁體有不同正字」的字;刻意不收繁簡同形字(干/后/里/面/别…),
# 否則誤報會淹沒真正的殘留。
SIMPLIFIED = set(
    "会检节优关单说应网时发员设计图数据库务处现让该这个为与从对问题认证过还门间类结构"
    "态断报错输级统执试验测环变换显释义详价终经营导线条几连边远进运达迁选规则记录实"
    "调护监觉简杂难标确识码农层联华龙凤见观论坛专业师传载积极际组织备额筑础脑储学写宽"
    "宝审尽属岁币帅归当彻东车长贝页风马鸟鱼举兴广产众万历双击键盘"
    # 以下是本書題材(醫療 / 特教 / 家庭)高頻、而原表沒收的簡體字
    "们么儿气泪脏肠养纤维练习惯谈话语训览怀虑绪齿龄汉药医疗闹妈亲园钱买卖饭视听读张"
)

# 命中任一詞,該章就必須帶醫療免責框。
MEDICAL_TRIGGERS = (
    "帝拔癲", "Depakine", "valproate", "丙戊酸", "抗癲癇藥", "血藥濃度",
    "生酮飲食", "類固醇", "停藥", "調藥", "劑量", "癲能停",
)
MED_DISCLAIMER = "醫療免責"

# 主線一律用化名。真名、校名等識別詞寫在 .privacy_terms(已 gitignore),一行一個;
# 沒有那個檔就只擋下面硬編的這幾個。
BASE_PRIVATE_TERMS = ("Jordan",)
APPENDIX_D_PREFIX = "附錄D"

failures: list[str] = []


def chapters() -> list[pathlib.Path]:
    return sorted(
        p for p in ROOT.glob("*.md")
        if not p.name.startswith(BOOK_TITLE)
        and p.name not in ("BUILD_STANDARD.md", "README.md", "CHANGELOG.md")
    )


def private_terms() -> tuple[str, ...]:
    extra = ROOT / ".privacy_terms"
    if not extra.exists():
        return BASE_PRIVATE_TERMS
    words = [w.strip() for w in extra.read_text(encoding="utf-8").splitlines()]
    return BASE_PRIVATE_TERMS + tuple(w for w in words if w and not w.startswith("#"))


def check_diagram_refs() -> None:
    for path in chapters():
        for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = ROOT / m.group(1)
            if not target.exists():
                failures.append(f"{path.name}: 引用了不存在的圖 {m.group(1)}")


def check_simplified() -> None:
    for path in chapters():
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for ch in line:
                if ch in SIMPLIFIED:
                    failures.append(f"{path.name}:{i} 混入簡體字「{ch}」")


def check_medical_disclaimer() -> None:
    """【WHY】本書讀者是家長。一章若寫了藥名、劑量或飲食療法,卻沒有把「這不是醫囑」
    講在同一章裡,讀者不會翻回序言去找免責——他會直接照著做。跨章的免責等於沒有免責。
    """
    for path in chapters():
        text = path.read_text(encoding="utf-8")
        hits = [t for t in MEDICAL_TRIGGERS if t in text]
        if hits and MED_DISCLAIMER not in text:
            failures.append(
                f"{path.name}: 出現醫療內容({'、'.join(hits[:3])})卻沒有「{MED_DISCLAIMER}」框"
            )


def check_privacy() -> None:
    """【WHY】本書是雙軌:主線是任何家長都能套用的通用方法書,個案細節只收在附錄D。
    真名或校名一旦漏進主線,去識別化就破了——而這種洩漏不可回收(書已經發出去了)。
    """
    terms = private_terms()
    for path in chapters():
        if path.name.startswith(APPENDIX_D_PREFIX):
            continue
        text = path.read_text(encoding="utf-8")
        for term in terms:
            if term in text:
                failures.append(f"{path.name}: 主線章節出現可識別詞「{term}」(應只在附錄D)")


def check_scenarios() -> None:
    """情境百景(第七篇)的骨架完整性。

    【WHY】五十個情境用同一副七段骨架寫成,而人在寫第三十七景的時候一定會漏段——
    漏掉的通常是「沒有這套方法的窘境」(因為它最難寫)或「可用工具」(因為它最像廢話)。
    漏了讀者不會抗議,他只會覺得這一景比較空。所以讓機器數。
    """
    required = ("**背景**", "**問題**", "**需要的技能**", "**可用工具**",
                "**這本書怎麼做**", "**沒有這套方法的窘境**", "**效益**",
                "💡 君之一席話", "🔍 進階點評")
    seen: dict[int, str] = {}
    for path in chapters():
        text = path.read_text(encoding="utf-8")
        if "情境" not in path.name and not re.search(r"^## 情境 \d+", text, re.M):
            continue
        blocks = re.split(r"(?m)^## (情境 (\d+)　.*)$", text)
        # split 後的結構:[前言, 標題, 編號, 內文, 標題, 編號, 內文, …]
        for i in range(1, len(blocks), 3):
            title, number, body = blocks[i], int(blocks[i + 1]), blocks[i + 2]
            if number in seen:
                failures.append(f"情境編號 {number} 重複({seen[number]} 與 {path.name})")
            seen[number] = path.name
            for token in required:
                if token not in body:
                    failures.append(f"{path.name}「{title}」缺少「{token}」段")
    if seen:
        expected = set(range(1, max(seen) + 1))
        for missing in sorted(expected - set(seen)):
            failures.append(f"情境編號 {missing} 不存在(編號必須連續)")


def check_glossary() -> None:
    """術語表(附錄F)不得列出正文沒有的詞。

    【WHY】術語表是「補寫」出來的——寫的時候是憑印象回想書裡用過什麼縮寫,
    於是很容易列進一個其實沒出現、或後來被改掉的詞。
    讀者查得到、卻在正文找不到,比沒有術語表更糟。
    """
    glossary = ROOT / "附錄F_術語表.md"
    if not glossary.exists():
        return
    body = "\n".join(
        p.read_text(encoding="utf-8") for p in chapters() if p.name != glossary.name
    )
    for m in re.finditer(r"(?m)^\| \*\*([A-Za-z][A-Za-z0-9/–\- ]{1,24})\*\*", glossary.read_text(encoding="utf-8")):
        term = m.group(1).strip()
        # 斜線或連字號並列的縮寫(WES／WGS、M01–M10)拆開比對,任一出現即可
        parts = [t.strip() for t in re.split(r"[/–]", term) if t.strip()]
        if not any(p in body for p in parts):
            failures.append(f"術語表列了「{term}」,但正文沒有出現")


def check_cross_references() -> None:
    """書中的「第 N 章」與「附錄 X」必須真的存在。

    【WHY】全書有數百處交叉引用,而章號在補強過程中一路從 34 加到 49。
    引用指向不存在的章,讀者會翻空;更糟的是指向**存在但錯誤**的章——
    那種錯誤沒有任何自動化以外的方法能發現。
    """
    existing_ch = {int(p.name[:2]) for p in ROOT.glob("[0-9][0-9]_*.md")}
    existing_apx = {p.name.split("_")[0].replace("附錄", "") for p in ROOT.glob("附錄*_*.md")}
    for path in chapters():
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"第\s*(\d{1,2})\s*章", text):
            number = int(m.group(1))
            if number not in existing_ch:
                failures.append(f"{path.name}: 引用了不存在的第 {number} 章")
        for m in re.finditer(r"附錄\s*([A-Z])", text):
            if m.group(1) not in existing_apx:
                failures.append(f"{path.name}: 引用了不存在的附錄 {m.group(1)}")


def check_build_is_current() -> None:
    """在暫存目錄重跑一次 _build.py,比對產物是否與已提交的一致。"""
    html = ROOT / f"{BOOK_TITLE}.html"
    merged = ROOT / f"{BOOK_TITLE}_全書.md"
    if not html.exists() or not merged.exists():
        failures.append("建置產物不存在,請先跑 python3 _build.py")
        return
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        for p in chapters():
            shutil.copy2(p, work)
        shutil.copy2(ROOT / "_build.py", work)
        shutil.copy2(ROOT / "cover.svg", work)
        shutil.copytree(ROOT / "diagrams", work / "diagrams")
        proc = subprocess.run(
            [sys.executable, "_build.py"], cwd=work, capture_output=True, text=True
        )
        if proc.returncode != 0:
            failures.append(f"_build.py 執行失敗:{proc.stderr.strip()[:300]}")
            return
        for name, committed in ((f"{BOOK_TITLE}.html", html), (f"{BOOK_TITLE}_全書.md", merged)):
            fresh = (work / name).read_bytes()
            if fresh != committed.read_bytes():
                failures.append(
                    f"{name} 與書稿不同步(重建後有差異)——書稿改了卻忘記重跑 _build.py"
                )


def check_html_id_uniqueness() -> None:
    """21 張 SVG 原生內嵌進同一份 HTML,id 若重複,url(#…) 會解析到第一個而非自己的定義。"""
    html = ROOT / f"{BOOK_TITLE}.html"
    if not html.exists():
        return
    text = html.read_text(encoding="utf-8")
    ids = re.findall(r'\bid="([^"]+)"', text)
    dup = {k: v for k, v in collections.Counter(ids).items() if v > 1}
    if dup:
        failures.append(f"HTML 有重複 id:{sorted(dup)[:8]}(共 {len(dup)} 個)")
    defined = set(ids)
    refs = set(re.findall(r"url\(#([^)]+)\)", text))
    for missing in sorted(refs - defined):
        failures.append(f"HTML 內 url(#{missing}) 指向不存在的 id")


def main() -> int:
    check_diagram_refs()
    check_simplified()
    check_medical_disclaimer()
    check_privacy()
    check_scenarios()
    check_glossary()
    check_cross_references()
    check_build_is_current()
    check_html_id_uniqueness()

    if failures:
        print(f"\n✗ 書稿檢查 FAILED({len(failures)} 項):")
        for f in failures[:40]:
            print(f"    - {f}")
        if len(failures) > 40:
            print(f"    …另有 {len(failures) - 40} 項")
        return 1
    print("✓ 書稿檢查全數通過(圖引用、簡體字、醫療免責、去識別化、情境骨架、術語表、交叉引用、建置同步、HTML id)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
