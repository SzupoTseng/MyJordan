"""十組功能性數學教材(第四篇)與題目產生器。

【WHY 要有題目產生器】
家長最容易放棄的不是「教」,是「每天想題目」。第 21 章要求每次 15 分鐘、
每週 3–4 次——那是一年上百組題目。手寫會斷,所以這裡把它自動化。

【WHY 產生器吃 seed】
同一個 seed 產生同一批題目,這樣:
① 測試可以驗;② 家長可以把「上週那份」重印一次(孩子需要重複);
③ 兩位照顧者可以用同一份題目,比較結果才有意義。
"""
from __future__ import annotations

import random
from dataclasses import dataclass

DIMENSIONS: dict[str, str] = {
    "D1": "數值與大小辨識",
    "D2": "金錢與等價交換",
    "D3": "時間序列與指令鏈",
}

# 台鐵車種與票價區間(用於題目;數值為示意,實際請用孩子常搭的區間表)
_TRAINS: tuple[tuple[str, int], ...] = (
    ("區間車", 150), ("莒光號", 240), ("自強號", 400), ("普悠瑪", 420), ("太魯閣號", 430),
)
_NOTES: tuple[int, ...] = (100, 500, 1000)
_COINS: tuple[int, ...] = (1, 5, 10, 50)


@dataclass(frozen=True)
class Material:
    code: str
    name: str
    dimension: str
    trains: str          # 練什麼
    chapter: int         # 對應章節
    has_drill: bool      # 是否有自動題目產生器


_MATERIALS: tuple[Material, ...] = (
    Material("M01", "誰比較貴", "D1", "兩個數字比大小", 22, True),
    Material("M02", "身高檢查員", "D1", "比小與規則限制", 22, True),
    Material("M03", "車廂點名", "D1", "指物數數與序數", 22, True),
    Material("M04", "付錢大作戰", "D2", "面額辨識與『夠不夠』", 23, True),
    Material("M05", "火車便當", "D2", "等值提取", 24, True),
    Material("M06", "逼逼看餘額", "D2", "數值遞減與消費因果", 24, True),
    Material("M07", "紀念品找零", "D2", "找零的動作鏈", 25, True),
    Material("M08", "時刻表", "D3", "數字比對與時間錨定", 26, True),
    Material("M09", "先…然後…", "D3", "先後順序", 26, True),
    Material("M10", "進站計時器", "D3", "等待耐受", 26, False),
)

MATERIALS: dict[str, Material] = {m.code: m for m in _MATERIALS}


def all_materials() -> tuple[Material, ...]:
    return _MATERIALS


def get_material(code: str) -> Material:
    normalized = code.strip().upper()
    if normalized not in MATERIALS:
        raise KeyError(f"未知教材 {code!r};可用:{', '.join(MATERIALS)}")
    return MATERIALS[normalized]


@dataclass(frozen=True)
class Question:
    """一道題目。

    `prompt` 是**要唸出口的台詞**,不是題幹——第四篇的原則是家長照著唸。
    `answer` 給大人對答案用,列印給孩子的版本不會有它。
    """

    material: str
    prompt: str
    answer: str
    hint: str = ""


def _pair(rng: random.Random) -> tuple[tuple[str, int], tuple[str, int]]:
    a, b = rng.sample(_TRAINS, 2)
    return a, b


def _m01(rng: random.Random, role: str) -> Question:
    (n1, p1), (n2, p2) = _pair(rng)
    return Question(
        "M01",
        f"{role}！今天我們要出車。{n1} {p1} 元、{n2} {p2} 元，"
        f"哪一個數字比較大？哪一張車票比較貴？",
        f"{n1 if p1 > p2 else n2}（{max(p1, p2)} 元）",
        "答錯時唸口訣：「數字前面比較長的，就是比較大的。」",
    )


def _m02(rng: random.Random, role: str) -> Question:
    rides = [("大怒神", 140), ("海盜船", 130), ("旋轉木馬", 110), ("急流泛舟", 120)]
    a, b = rng.sample(rides, 2)
    return Question(
        "M02",
        f"{role}是安全檢查員。{a[0]}要 {a[1]} 公分，{b[0]}要 {b[1]} 公分。"
        f"哪一個數字比較小？哪一個設施比較矮的人就能玩？",
        f"{a[0] if a[1] < b[1] else b[0]}（{min(a[1], b[1])} 公分）",
        "進階：量他的身高，問「你可不可以玩？」",
    )


def _m03(rng: random.Random, role: str) -> Question:
    colors = ["紅", "藍", "黃", "綠", "黑"]
    count = rng.randint(3, 5)
    picked = rng.sample(colors, count)
    which = rng.choice(["總共幾輛", "第一輛", "最後一輛"])
    if which == "總共幾輛":
        return Question("M03", f"{role}幫忙點名，這裡總共有幾輛火車？", f"{count} 輛",
                        "★ 必須用手指逐一點數，不可以用眼睛掃")
    if which == "第一輛":
        return Question("M03", "第一輛是什麼顏色？", f"{picked[0]}色",
                        f"排列順序：{'、'.join(picked)}")
    return Question("M03", "最後一輛是什麼顏色？", f"{picked[-1]}色",
                    f"排列順序：{'、'.join(picked)}")


def _m04(rng: random.Random, role: str) -> Question:
    price = rng.choice((800, 999, 899, 450, 650))
    enough = min(n for n in _NOTES if n >= price) if price <= max(_NOTES) else 1000
    return Question(
        "M04",
        f"{role}，門票要 {price} 元。桌上有 100 元和 1000 元，"
        f"你要拿哪一張給售票員，錢才夠？",
        f"{enough} 元",
        "答錯時唸口訣：「一百元太小了，買不到門票。我們要拿藍色的一千元。」",
    )


def _m05(rng: random.Random, role: str) -> Question:
    price = rng.choice((100, 500))
    return Question(
        "M05",
        f"{role}肚子餓了，便當要 {price} 元。請從桌上拿『剛好一張』{price} 元給我。",
        f"一張 {price} 元",
        "★ 桌上要同時有其他面額當干擾；成功後說「剛剛好，不用找錢」",
    )


def _m06(rng: random.Random, role: str) -> Question:
    before = rng.choice((200, 300, 500))
    fare = rng.choice((15, 25, 50))
    return Question(
        "M06",
        f"{role}，進站的時候卡片裡有 {before} 元，出站變成 {before - fare} 元。"
        f"數字是變大還是變小？錢是變多還是變少？",
        f"變小／變少（付了 {fare} 元）",
        "口訣：「搭火車，逼一聲，卡片裡的錢會變少。」",
    )


def _m07(rng: random.Random, role: str) -> Question:
    price, paid = rng.choice(((450, 500), (380, 500), (850, 1000), (180, 200)))
    change = paid - price
    return Question(
        "M07",
        f"{role}要買 {price} 元的紀念品，你給了 {paid} 元。"
        f"店員找你錢的時候，你要做什麼？",
        f"左手等著拿 {change} 元，然後放進錢包關好",
        "★ 練的是動作鏈，不是心算。口訣：「等一下，錢還沒拿完。」",
    )


def _m08(rng: random.Random, role: str) -> Question:
    base = rng.choice((13, 14, 15, 16))
    table = [(f"{base}:00", "區間車"), (f"{base}:30", "自強號"), (f"{base + 1}:00", "普悠瑪")]
    idx = rng.randrange(len(table))
    now, train = table[idx]
    return Question(
        "M08",
        f"{role}，時刻表上有 {table[0][0]} {table[0][1]}、{table[1][0]} {table[1][1]}、"
        f"{table[2][0]} {table[2][1]}。現在電子鐘是 {now}，哪一輛車要來了？",
        train,
        "找不到時：把電子鐘拿到時刻表旁邊，讓兩個數字物理上靠在一起",
    )


def _m09(rng: random.Random, role: str) -> Question:
    pairs = [("坐動物巴士", "玩急流泛舟"), ("擦黑板", "倒垃圾"), ("洗手", "吃飯")]
    a, b = rng.choice(pairs)
    reverse = rng.random() < 0.4
    if reverse:
        return Question("M09", f"在{b}之前，要先{a}。請問第一個要做什麼？", a,
                        "★ 逆向語序：卡住是正常的，可先用兩張圖卡排順序")
    return Question("M09", f"我們要先{a}，然後才{b}。請問第一個要做什麼？", a,
                    "第二層：把圖卡打亂，請他自己排順序")


_DRILLS = {
    "M01": _m01, "M02": _m02, "M03": _m03, "M04": _m04, "M05": _m05,
    "M06": _m06, "M07": _m07, "M08": _m08, "M09": _m09,
}


def generate(code: str, count: int = 5, seed: int | None = None,
             role: str = "維修長") -> list[Question]:
    """產生一組題目。

    M10 沒有題目——它是一段流程(把計時器接到所有等待場合),
    硬要產生題目反而會讓家長以為它是紙上作業。
    """
    material = get_material(code)
    if not material.has_drill:
        raise ValueError(
            f"{material.code}（{material.name}）沒有題目：它是流程，不是題庫。見第 26 章。"
        )
    if count < 1:
        raise ValueError("count 至少要 1")
    if count > 30:
        raise ValueError("count 上限 30：第 21 章的原則是每次不超過 15 分鐘")
    rng = random.Random(seed)
    return [_DRILLS[material.code](rng, role) for _ in range(count)]
