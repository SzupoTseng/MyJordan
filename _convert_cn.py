#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""繁體中文稿 -> 简体中文稿（tw2sp：含台灣用語轉大陸用語）。輸出到 cn/。

系列標準 BUILD_STANDARD.md §6：简体版是**機械轉換，不是翻譯**。
用法：python3 _convert_cn.py  然後  cd cn && python3 _build.py

依賴：OpenCC（`pip install opencc-python-reimplemented` 或系統套件）。
WSL 若無 pip，可改用 Windows python 執行（多半已裝 opencc）。

【WHY 這本書要多做一段本地化檢查】
本書題材是特殊教育與醫療，而兩岸的制度用語不同且**不可機械互換**：
「小作所」「庇護工場」「鑑輔會」「身心障礙證明」「悠遊卡」是台灣制度的專名，
直接轉成简体字之後，字對了、制度卻是錯的。因此轉換後會列出這些詞的出現位置，
提醒譯者逐一改寫成當地對應制度或加註說明——**這一步不能自動化**。
"""
import glob
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import opencc
except ImportError:  # pragma: no cover - 環境相依
    sys.exit("需要 OpenCC：pip install opencc-python-reimplemented\n"
             "（WSL 無 pip 時，可改用 Windows python 執行本檔）")

c = opencc.OpenCC("tw2sp")

# 轉換後的修正表。分兩類:
#   ① OpenCC 不轉的台灣專用代名詞
#   ② OpenCC **轉錯**的詞——tw2sp 會做台灣用語→大陸用語的詞彙替換,
#      而詞彙替換是看不懂語境的。
#
# 【真實踩到的一個】「核心」→「内核」。
#   tw2sp 認為台灣的「核心」對應大陸的「内核」——那在計算機語境（kernel）成立，
#   但本書的「三大核心」是 core，不是 kernel。首次轉換後全書出現 335 個「内核」，
#   連檔名都變成「07_三内核总览.md」。
#   這正是 §6 說「机械转换不是翻译」的具體樣子：字全對，意思全錯。
EXTRA = {
    "牠": "它", "妳": "你", "祂": "它",
    "内核": "核心",   # ← 見上方說明；本書無 kernel 語境，可安全全域還原
}

# 台灣制度專名：轉成简体字之後仍然是「台灣的制度」，需要人工在地化。
LOCALE_TERMS = (
    "小作所", "社區日間作業設施", "庇護工場", "鑑輔會", "身心障礙證明",
    "特教學校", "適性輔導安置", "職業重建個案管理", "就業服務員",
    "悠遊卡", "一卡通", "台鐵", "自強號", "區間車", "普悠瑪",
    "健保卡", "勞保", "勞退", "國民年金", "法律扶助",
)

BOOK = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BOOK, "cn")


def post(text: str) -> str:
    for k, v in EXTRA.items():
        text = text.replace(k, v)
    return text


def src_files() -> list[str]:
    files = []
    pre = glob.glob(os.path.join(BOOK, "00_*.md"))
    if pre:
        files.append(pre[0])
    for n in range(1, 50):
        cand = glob.glob(os.path.join(BOOK, "%02d_*.md" % n))
        if cand:
            files.append(cand[0])
    for apx in sorted(glob.glob(os.path.join(BOOK, "附錄*_*.md"))):
        files.append(apx)
    return files


def convert_build_script() -> None:
    """把 _build.py 一併簡體化成 cn/_build.py（系列標準 §6）。

    【WHY 只轉字串常數與註解，不動程式碼】
    OpenCC 會把中文一律轉換，包含 `title_for()` 裡的在地化 regex——
    而那些 regex 要比對的是**简体書稿**裡的「第N章」「附录」，所以確實該轉。
    但 Python 的語法與識別字必須原封不動，因此這裡逐行處理：
    只轉「非 ASCII 的段落」，ASCII 部分（關鍵字、變數名）一個字都不碰。
    """
    src = os.path.join(BOOK, "_build.py")
    text = open(src, encoding="utf-8").read()
    # OpenCC 對 ASCII 不做任何事,所以整檔轉換是安全的——
    # 它只會動到中文字元(字串常數、註解、docstring)。
    # 【WHY newline="\n"】這支腳本多半在 Windows python 上跑(WSL 常常沒有 OpenCC),
    # 而 Windows 的 open(..., "w") 預設會把 \n 寫成 \r\n。
    # 結果是:每次重跑 cn/,整批 57 個檔案都會變成「有變更」——而內容其實一個字都沒動。
    # 固定寫 LF,重跑才會是冪等的。
    cn_text = post(c.convert(text))
    with open(os.path.join(OUT, "_build.py"), "w", encoding="utf-8", newline="\n") as w:
        w.write(cn_text)
    print("_build.py -> cn/_build.py")


def copy_assets() -> None:
    """封面與流程圖照抄（SVG 內的中文標題不轉——那會讓圖與简体正文不一致，
    但轉了又會動到 SVG 結構。折衷：轉純文字節點的中文，其餘保持原樣）。"""
    shutil.copy2(os.path.join(BOOK, "cover.svg"), os.path.join(OUT, "cover.svg"))
    diagrams_out = os.path.join(OUT, "diagrams")
    os.makedirs(diagrams_out, exist_ok=True)
    n = 0
    for svg in sorted(glob.glob(os.path.join(BOOK, "diagrams", "*.svg"))):
        text = open(svg, encoding="utf-8").read()
        # 只轉 >文字< 之間的內容,不碰標籤與屬性
        cn_svg = re.sub(r">([^<>]*[一-鿿][^<>]*)<",
                        lambda m: ">" + post(c.convert(m.group(1))) + "<", text)
        with open(os.path.join(diagrams_out, os.path.basename(svg)), "w",
                  encoding="utf-8", newline="\n") as w:
            w.write(cn_svg)
        n += 1
    print("assets -> cn/cover.svg + cn/diagrams/(%d 張)" % n)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    hits: dict[str, int] = {}
    count = 0
    for path in src_files():
        base = os.path.basename(path)
        text = open(path, encoding="utf-8").read()
        for term in LOCALE_TERMS:
            n = text.count(term)
            if n:
                hits[term] = hits.get(term, 0) + n
        cn_text = post(c.convert(text))
        cn_base = post(c.convert(base))
        with open(os.path.join(OUT, cn_base), "w", encoding="utf-8", newline="\n") as w:
            w.write(cn_text)
        print(base, "->", cn_base)
        count += 1

    convert_build_script()
    copy_assets()

    print("\nconverted %d files into %s" % (count, OUT))
    if hits:
        print("\n⚠️ 以下是台灣制度／在地專名，機械轉換只換了字，沒有換制度——")
        print("   請逐一改寫成當地對應制度，或加註說明後再發布：")
        for term, n in sorted(hits.items(), key=lambda kv: -kv[1]):
            print(f"   · {term}　出現 {n} 次")
        print("\n   ★ 本書涉及醫療與社福制度，字對了而制度錯了，會誤導讀者。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
