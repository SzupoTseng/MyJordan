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
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import opencc
except ImportError:  # pragma: no cover - 環境相依
    sys.exit("需要 OpenCC：pip install opencc-python-reimplemented\n"
             "（WSL 無 pip 時，可改用 Windows python 執行本檔）")

c = opencc.OpenCC("tw2sp")

# OpenCC 不轉的台灣專用代名詞 -> 大陸標準简体
EXTRA = {"牠": "它", "妳": "你", "祂": "它"}

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
        with open(os.path.join(OUT, cn_base), "w", encoding="utf-8") as w:
            w.write(cn_text)
        print(base, "->", cn_base)
        count += 1

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
