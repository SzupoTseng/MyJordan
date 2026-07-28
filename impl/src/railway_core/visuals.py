"""列印用資產產生器:視覺檢核卡、聊天券、價格字卡、時刻表(第 13、10、21、26 章)。

【WHY 產出 SVG 而不是 PDF 或圖片】
SVG 是純文字,可以用瀏覽器直接開、直接列印,不需要安裝任何東西;
而且家長可以用文字編輯器把「擦黑板」改成「掃地」,不必回來重跑程式。
這符合本書的一貫立場:工具要能被使用者接手,而不是綁住他。

【尺寸】全部以 A4 橫式（297×210mm）為基準,列印時選「符合頁面」即可。
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

_W, _H = 1123, 794          # A4 橫式 @96dpi 的近似像素
_INK = "#1d2230"
_MUT = "#5a6378"
_GOLD = "#9a6a1a"
_LINE = "#c9c3b4"


def _header(title: str, subtitle: str) -> str:
    return (
        f'<rect width="{_W}" height="{_H}" fill="#ffffff"/>'
        f'<text x="56" y="66" font-size="34" font-weight="700" fill="{_INK}">{escape(title)}</text>'
        f'<text x="56" y="98" font-size="17" fill="{_MUT}">{escape(subtitle)}</text>'
        f'<path d="M56 116 H{_W - 56}" stroke="#f4b860" stroke-width="3"/>'
    )


def _svg(body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W} {_H}" '
        f'font-family="\'Noto Sans CJK TC\',\'PingFang TC\',\'Microsoft JhengHei\',sans-serif">'
        f"{body}</svg>\n"
    )


@dataclass(frozen=True)
class Asset:
    filename: str
    content: str


def checklist_card(tasks: list[str], title: str = "小幫手任務卡",
                   role: str = "維修長") -> Asset:
    """三格（或 N 格）視覺檢核卡。

    第 13 章的規格:三格起步、打勾由孩子自己做、卡片是憑證不是提醒。
    """
    if not tasks:
        raise ValueError("至少要有一項任務")
    if len(tasks) > 5:
        # 【WHY 擋在 5】第 13 章:三格起步。超過五格的卡片,在現場沒有人用得起來。
        raise ValueError("一張卡最多 5 格；三格起步，做穩了再加（第 13 章）")

    n = len(tasks)
    gap, margin = 24, 56
    width = (_W - margin * 2 - gap * (n - 1)) / n
    parts = [_header(title, f"{role}　完成一項自己打一個勾　全部打完交回卡片")]
    for i, task in enumerate(tasks):
        x = margin + i * (width + gap)
        parts.append(
            f'<rect x="{x:.1f}" y="180" width="{width:.1f}" height="420" rx="18" '
            f'fill="#fbf8f0" stroke="{_LINE}" stroke-width="3"/>'
            f'<text x="{x + width / 2:.1f}" y="228" text-anchor="middle" font-size="19" '
            f'fill="{_MUT}">車廂 {i + 1}</text>'
            f'<rect x="{x + 24:.1f}" y="252" width="{width - 48:.1f}" height="180" rx="10" '
            f'fill="#ffffff" stroke="{_LINE}" stroke-dasharray="8 6"/>'
            f'<text x="{x + width / 2:.1f}" y="350" text-anchor="middle" font-size="15" '
            f'fill="{_MUT}">（貼上實物照片）</text>'
            f'<text x="{x + width / 2:.1f}" y="482" text-anchor="middle" font-size="26" '
            f'font-weight="700" fill="{_INK}">{escape(task)}</text>'
            f'<rect x="{x + width / 2 - 34:.1f}" y="510" width="68" height="68" rx="10" '
            f'fill="#ffffff" stroke="{_INK}" stroke-width="3"/>'
        )
    parts.append(
        f'<text x="56" y="668" font-size="16" fill="{_MUT}">'
        f'交辦時不說長句：把卡片和筆交到他手上，手指第一格。執行中不催促。'
        f'卡住時先等 5–10 秒，再給手勢提示。</text>'
        f'<text x="56" y="700" font-size="16" fill="{_GOLD}">'
        f'★ 打勾必須由他自己做——那個動作本身就是「完工」的標記。</text>'
    )
    return Asset("checklist_card.svg", _svg("".join(parts)))


def token_board(count: int = 3, topic: str = "火車", minutes: int = 5) -> Asset:
    """聊天券與代幣板（第 10 章）。"""
    if not 1 <= count <= 6:
        raise ValueError("聊天券建議 1–6 張；太多會失去邊界的意義（第 10 章）")
    parts = [_header(f"{topic}聊天券",
                     f"一張 = {minutes} 分鐘　交出券才開始　用完就結束，不預支、不累積")]
    gap, margin = 30, 56
    width = (_W - margin * 2 - gap * (count - 1)) / count
    for i in range(count):
        x = margin + i * (width + gap)
        parts.append(
            f'<rect x="{x:.1f}" y="200" width="{width:.1f}" height="240" rx="16" '
            f'fill="#fdf3e3" stroke="#e8c88a" stroke-width="3"/>'
            f'<text x="{x + width / 2:.1f}" y="290" text-anchor="middle" font-size="30" '
            f'font-weight="700" fill="{_GOLD}">{escape(topic)}券</text>'
            f'<text x="{x + width / 2:.1f}" y="340" text-anchor="middle" font-size="22" '
            f'fill="{_INK}">{minutes} 分鐘</text>'
            f'<text x="{x + width / 2:.1f}" y="392" text-anchor="middle" font-size="15" '
            f'fill="{_MUT}">第 {i + 1} 張</text>'
        )
    parts.append(
        f'<text x="56" y="510" font-size="18" fill="{_INK}">非約定時段他提起時：一個字都不用說，用手指向這些券。</text>'
        f'<text x="56" y="548" font-size="18" fill="{_INK}">固定台詞（每次一樣）：「現在不是{escape(topic)}時間，請把券收好。」</text>'
        f'<text x="56" y="600" font-size="17" fill="#9a3b2f">三個禁止：不可當處罰沒收 · 不可額外多給 · 不可在他快爆發時提前給</text>'
    )
    return Asset("token_board.svg", _svg("".join(parts)))


def price_cards(items: list[tuple[str, int]], title: str = "價格字卡") -> Asset:
    """價格字卡（M01/M04/M05 用）。"""
    if not items:
        raise ValueError("至少要有一項商品")
    if len(items) > 8:
        raise ValueError("一張最多 8 個項目，太多會讓他無法聚焦")
    parts = [_header(title, "用真實的價格；每次只拿兩張出來比較（第 22 章）")]
    cols = 4 if len(items) > 3 else len(items)
    rows = (len(items) + cols - 1) // cols
    gap, margin = 26, 56
    width = (_W - margin * 2 - gap * (cols - 1)) / cols
    height = min(220.0, (_H - 260 - gap * (rows - 1)) / rows)
    for i, (name, price) in enumerate(items):
        r, c = divmod(i, cols)
        x = margin + c * (width + gap)
        y = 190 + r * (height + gap)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="14" '
            f'fill="#ffffff" stroke="{_LINE}" stroke-width="3"/>'
            f'<text x="{x + width / 2:.1f}" y="{y + height * 0.42:.1f}" text-anchor="middle" '
            f'font-size="26" fill="{_INK}">{escape(name)}</text>'
            f'<text x="{x + width / 2:.1f}" y="{y + height * 0.78:.1f}" text-anchor="middle" '
            f'font-size="46" font-weight="700" fill="{_GOLD}">{price} 元</text>'
        )
    return Asset("price_cards.svg", _svg("".join(parts)))


def timetable_card(rows: list[tuple[str, str]], title: str = "火車時刻表") -> Asset:
    """極簡時刻表（M08 用）。第 26 章:一開始只放 3 班。"""
    if not 1 <= len(rows) <= 5:
        raise ValueError("時刻表放 1–5 班；真實時刻表會直接淹沒他（第 26 章）")
    parts = [_header(title, "電子鐘上的數字，跟哪一個一樣？")]
    for i, (time_text, train) in enumerate(rows):
        y = 210 + i * 110
        parts.append(
            f'<rect x="120" y="{y}" width="{_W - 240}" height="86" rx="12" '
            f'fill="{"#fbf8f0" if i % 2 == 0 else "#ffffff"}" stroke="{_LINE}" stroke-width="2"/>'
            f'<text x="200" y="{y + 58}" font-size="46" font-weight="700" fill="{_INK}">'
            f'{escape(time_text)}</text>'
            f'<text x="480" y="{y + 58}" font-size="40" fill="{_GOLD}">{escape(train)}</text>'
        )
    return Asset("timetable_card.svg", _svg("".join(parts)))


def task_analysis_card(steps: list[str], title: str = "工作分析步驟卡",
                       chaining: str = "後向連鎖") -> Asset:
    """工作分析的步驟卡與提示層級記錄表（第 36 章）。

    右側五欄記的是**提示層級**，不是「會／不會」——
    因為進步的樣子是「P → M → V → G → I」，
    而在「會／不會」的記法下，前三個月的紀錄會全部是「不會」，
    然後家長就放棄了。
    """
    if not steps:
        raise ValueError("至少要有一個步驟")
    if len(steps) > 12:
        # 【WHY 擋在 12】超過 12 步的表格，在現場沒有人邊做邊記得完。
        # 真的超過，代表這個技能應該先切成兩份工作分析。
        raise ValueError("一張卡最多 12 步；超過請切成兩份工作分析（第 36 章）")

    row_h = min(46.0, (560 - 40) / len(steps))
    parts = [_header(title, f"{chaining}　·　記錄「提示層級」，不是「會或不會」")]
    parts.append(
        f'<text x="700" y="176" font-size="15" fill="{_MUT}">'
        f'I 獨立　G 手勢　V 口頭　M 示範　P 肢體協助</text>'
    )
    for col in range(5):
        x = 700 + col * 76
        parts.append(f'<rect x="{x}" y="188" width="70" height="28" rx="6" '
                     f'fill="#fbf8f0" stroke="{_LINE}"/>'
                     f'<text x="{x + 35}" y="208" text-anchor="middle" font-size="13" '
                     f'fill="{_MUT}">日期</text>')
    for i, step in enumerate(steps):
        y = 224 + i * row_h
        parts.append(
            f'<rect x="56" y="{y:.1f}" width="620" height="{row_h - 6:.1f}" rx="8" '
            f'fill="{"#fbf8f0" if i % 2 == 0 else "#ffffff"}" stroke="{_LINE}"/>'
            f'<text x="76" y="{y + row_h / 2 + 2:.1f}" font-size="19" fill="{_MUT}">{i + 1}</text>'
            f'<text x="112" y="{y + row_h / 2 + 2:.1f}" font-size="20" fill="{_INK}">'
            f'{escape(step)}</text>'
        )
        for col in range(5):
            x = 700 + col * 76
            parts.append(f'<rect x="{x}" y="{y:.1f}" width="70" height="{row_h - 6:.1f}" rx="6" '
                         f'fill="#ffffff" stroke="{_LINE}"/>')
    parts.append(
        f'<text x="56" y="752" font-size="15" fill="{_GOLD}">'
        f'★ 每一步應該是 3–7 秒可完成、且大人能一眼看出他做了沒有的動作。</text>'
    )
    return Asset("task_analysis_card.svg", _svg("".join(parts)))


# ─────────────────────────────────────────────────────────────
# 記錄表
#
# 【WHY 這些要能列印,而不是只存在 CLI 裡】
# 書中每一章都給了表格範本,但真正每天要填的那幾張,家長得自己畫格子——
# 而「自己畫格子」這件事,是記錄中斷最常見的第一個原因。
# 這幾張表刻意做成「一張紙一個月」:貼在冰箱上，填完就是一份趨勢。
# ─────────────────────────────────────────────────────────────


def _grid(x: float, y: float, widths: list[float], rows: int,
          row_h: float, headers: list[str]) -> str:
    """畫一張表格：表頭 + N 列空格。"""
    parts = []
    cx = x
    # 【WHY strict=True】欄寬與表頭的數量若不一致,zip 會靜默截斷——
    # 表格會少一欄,而印出來的紙上沒有任何跡象顯示少了東西。
    # 這正是表格產生器最容易犯、也最難發現的一種錯。ruff B905 抓到的。
    for width, title in zip(widths, headers, strict=True):
        parts.append(
            f'<rect x="{cx:.1f}" y="{y:.1f}" width="{width:.1f}" height="{row_h:.1f}" '
            f'fill="#f0ebdd" stroke="{_LINE}" stroke-width="1.5"/>'
            f'<text x="{cx + width / 2:.1f}" y="{y + row_h * 0.68:.1f}" text-anchor="middle" '
            f'font-size="13" font-weight="700" fill="{_INK}">{escape(title)}</text>'
        )
        cx += width
    for r in range(rows):
        cx = x
        ry = y + row_h * (r + 1)
        for width in widths:
            parts.append(
                f'<rect x="{cx:.1f}" y="{ry:.1f}" width="{width:.1f}" height="{row_h:.1f}" '
                f'fill="{"#fbf8f0" if r % 2 else "#ffffff"}" stroke="{_LINE}"/>'
            )
            cx += width
    return "".join(parts)


def daily_log(days: int = 31) -> Asset:
    """每日三指標記錄表（第 1 章）。一張紙一個月。"""
    if not 7 <= days <= 31:
        raise ValueError("一張表 7–31 天；更長會讓格子小到寫不下")
    headers = ["日期", "情緒回復\n（秒）", "任務\n交辦/獨立", "指令\n步數",
               "固著\n（分）", "睡眠\n（時）", "備註（睡不好、生病、換環境…）"]
    widths = [70.0, 90.0, 100.0, 70.0, 70.0, 70.0, 541.0]
    row_h = min(20.0, (620 - 190) / (days + 1))
    parts = [_header("每日記錄　三個數字，每天不超過三分鐘",
                     "第 1 章：沒有基線的努力，三個月後會變成一場關於「他到底有沒有進步」的爭吵")]
    parts.append(_grid(56, 170, widths, days, row_h, [h.replace("\n", " ") for h in headers]))
    parts.append(
        f'<text x="56" y="{170 + row_h * (days + 1) + 30:.1f}" font-size="13" fill="{_MUT}">'
        f'※ 沒有交辦任務的日子，「任務」欄留白，不要記 0——記 0 會把整週平均拉低。</text>'
        f'<text x="56" y="{170 + row_h * (days + 1) + 52:.1f}" font-size="13" fill="{_GOLD}">'
        f'※ 兩位照顧者要先對「起點事件」的定義：從皺眉算起，還是從出聲算起？寫下來，貼冰箱。</text>'
    )
    return Asset("daily_log.svg", _svg("".join(parts)))


def abc_form(rows: int = 12) -> Asset:
    """ABC 三聯式記錄表（第 35 章）。"""
    if not 4 <= rows <= 20:
        raise ValueError("一張表 4–20 筆；ABC 要寫得下前事與後果，格子不能太小")
    parts = [_header("ABC 記錄　行為定義：________________________",
                     "第 35 章：只記 B（「他今天又鬧了三次」）產不出任何結論")]
    widths = [64.0, 52.0, 230.0, 200.0, 265.0, 100.0]
    row_h = min(38.0, (600 - 200) / (rows + 1))
    parts.append(_grid(56, 178, widths, rows, row_h,
                       ["日期", "時間", "A 前事", "B 行為", "C 後果（他得到什麼）", "持續/功能"]))
    y = 178 + row_h * (rows + 1) + 28
    parts.append(
        f'<text x="56" y="{y:.1f}" font-size="13" fill="{_GOLD}">'
        f'※ C 欄寫「他因此得到了什麼」，不是「我做了什麼」。'
        f'「我罵了他」→ 應寫成「他得到 3 分鐘一對一注意」。</text>'
        f'<text x="56" y="{y + 22:.1f}" font-size="13" fill="{_MUT}">'
        f'※ A 欄不要寫「不知道／突然就」——那通常代表當時沒看到。'
        f'寫下你確實知道的：在做什麼、誰在場、剛被要求什麼。</text>'
        f'<text x="56" y="{y + 44:.1f}" font-size="13" fill="{_MUT}">'
        f'※ 功能：注意／逃避／實體物／感官。記滿兩週、至少 10 筆再下結論。</text>'
    )
    return Asset("abc_form.svg", _svg("".join(parts)))


def sleep_log(days: int = 28) -> Asset:
    """睡眠日誌（第 11 章）。地基②，最快見效的一塊。"""
    if not 7 <= days <= 31:
        raise ValueError("一張表 7–31 天")
    parts = [_header("睡眠日誌　每天 30 秒",
                     "第 11 章：訓練失效時，先查地基，再檢討方法")]
    widths = [80.0, 110.0, 110.0, 100.0, 100.0, 130.0, 381.0]
    row_h = min(20.0, (620 - 190) / (days + 1))
    parts.append(_grid(56, 170, widths, days, row_h,
                       ["日期", "就寢", "實際入睡", "起床", "夜醒次數",
                        "睡前1小時螢幕", "隔天狀態（好／普通／差）"]))
    y = 170 + row_h * (days + 1) + 30
    parts.append(
        f'<text x="56" y="{y:.1f}" font-size="13" fill="{_GOLD}">'
        f'※ 固定「起床時間」比固定就寢時間更有效——假日也不要差超過 1 小時。</text>'
        f'<text x="56" y="{y + 22:.1f}" font-size="13" fill="#9a3b2f">'
        f'※ 睡眠中反覆抽動、異常姿勢、大量流口水 → 要告訴醫師，那可能是夜間發作，不是睡不好。</text>'
    )
    return Asset("sleep_log.svg", _svg("".join(parts)))


def preference_form(items: list[str] | None = None) -> Asset:
    """偏好評估配對表（第 37 章）。找出真正的增強物。"""
    candidates = items or ["火車影片", "貼紙", "音樂", "幫老師做事", "小點心", "和爸爸散步"]
    if not 3 <= len(candidates) <= 8:
        raise ValueError("候選項目 3–8 個；太多會讓配對次數爆炸")
    pairs = [(a, b) for i, a in enumerate(candidates) for b in candidates[i + 1:]]
    parts = [_header("偏好評估　配對選擇",
                     "第 37 章：一樣東西是不是增強物，由行為的變化決定，不是由你決定")]
    parts.append(
        f'<text x="56" y="164" font-size="14" fill="{_INK}">候選項目：'
        f'{escape("　".join(candidates))}</text>'
        f'<text x="56" y="188" font-size="13" fill="{_MUT}">'
        f'每一對拿出兩樣實物，讓他選一樣。每對測 2 次，把選中的寫下來。</text>'
    )
    widths = [300.0, 220.0, 220.0]
    row_h = min(30.0, (560 - 210) / (len(pairs) + 1))
    parts.append(_grid(56, 206, widths, len(pairs), row_h, ["配對", "第 1 次選了", "第 2 次選了"]))
    for i, (a, b) in enumerate(pairs):
        parts.append(
            f'<text x="72" y="{206 + row_h * (i + 1) + row_h * 0.68:.1f}" font-size="13" '
            f'fill="{_INK}">{escape(a)}　vs　{escape(b)}</text>'
        )
    y = 206 + row_h * (len(pairs) + 1) + 28
    parts.append(
        f'<text x="56" y="{y:.1f}" font-size="13" fill="{_GOLD}">'
        f'※ 清單裡一定要放「非物品」的選項：一段單獨相處的時間、幫老師做一件特別的事。</text>'
        f'<text x="56" y="{y + 22:.1f}" font-size="13" fill="{_MUT}">'
        f'※ 偏好會變。每 2–3 個月重做一次，或當你發現「最近好像沒效了」時。</text>'
    )
    return Asset("preference_form.svg", _svg("".join(parts)))


ASSET_FILENAMES: tuple[str, ...] = (
    "checklist_card.svg", "token_board.svg", "price_cards.svg", "timetable_card.svg",
    "task_analysis_card.svg",
    "daily_log.svg", "abc_form.svg", "sleep_log.svg", "preference_form.svg",
)
