# railway_core —— 《慢車到站》的工具包

零依賴（只用 Python 標準庫）。`clone` 下來就能跑，不需要 `pip install`。

```bash
cd impl
python3 selftest.py                        # 三秒確認工具是好的（零依賴）

PYTHONPATH=src python3 -m railway_core.app init --code J --stage S1
PYTHONPATH=src python3 -m railway_core.app record --date 2026-03-02 \
    --recovery 190 --tasks 5/2 --sleep 7.5 --note "昨晚很晚睡"
PYTHONPATH=src python3 -m railway_core.app report --days 14
PYTHONPATH=src python3 -m railway_core.app gate S1 --set gesture_stop_rate=0.82
PYTHONPATH=src python3 -m railway_core.app drill M04 --count 8 --seed 7
PYTHONPATH=src python3 -m railway_core.app assets
```

---

## 它做什麼

| 指令 | 做什麼 | 對應章節 |
|------|--------|---------|
| `init` | 建立個案設定（代號、站別、角色稱號、固著主題） | 7、12、15 |
| `record` | 記錄一天的三個核心指標（不超過三分鐘） | 1 |
| `report` | 週報：中位數、趨勢，以及值得回頭看一眼的型態 | 1、11 |
| `gate` | 離站判定：三道門（能力／地基／照顧者） | 20 |
| `drill` | 產生教材題目（含逐字台詞與制約口訣） | 21–26 |
| **`abc`** | **記錄一筆 ABC 三聯式（前事／行為／後果）** | **35** |
| **`function`** | **統計行為功能，給出假設句與策略建議** | **35** |
| `assets` | 產生列印用 SVG | 10、13、21、26、36 |
| `redflags` | 顯示紅旗清單與「永遠不要」 | 3、11 |
| `stages` `materials` | 列出六站與十組教材 | 12、21 |

```bash
# ABC 記錄（第 35 章）：A 與 C 都是必填，且會擋掉「不知道」這類填法
PYTHONPATH=src python3 -m railway_core.app abc --date 2026-03-02 --time 16:20 \
    -a "剛被要求收玩具" -b "重複說火車 6 次、音量提高" \
    -c "我幫他收了玩具" --function escape --duration 4

PYTHONPATH=src python3 -m railway_core.app function
```

### `assets` 產出的九個檔案

**教具卡片**

| 檔名 | 是什麼 | 章 |
|------|--------|---|
| `checklist_card.svg` | 三格視覺任務檢核卡（最多 5 格） | 13 |
| `token_board.svg` | 聊天券與代幣板 | 10 |
| `price_cards.svg` | 價格字卡（M01／M04／M05 用） | 22–24 |
| `timetable_card.svg` | 極簡時刻表（最多 5 班） | 26 |
| `task_analysis_card.svg` | 工作分析步驟卡 + 提示層級記錄表（最多 12 步） | 36 |

**記錄表**（一張紙一個月，貼冰箱）

| 檔名 | 是什麼 | 章 |
|------|--------|---|
| `daily_log.svg` | 每日三指標記錄表 | 1 |
| `abc_form.svg` | ABC 三聯式記錄表 | 35 |
| `sleep_log.svg` | 睡眠日誌 | 11 |
| `preference_form.svg` | 偏好評估配對表 | 37 |

> **為什麼記錄表也要能列印**：書中每一章都給了表格範本，但真正每天要填的那幾張，
> 家長得自己畫格子——而「自己畫格子」是記錄中斷最常見的第一個原因。

用瀏覽器開啟後直接列印（選「符合頁面」），護貝後即可使用。SVG 是純文字，
你可以用任何文字編輯器把「擦黑板」改成「掃地」，不必回來重跑程式。

---

## 五個刻意的設計決定

**一、沒有姓名欄位。**
`Profile` 連存放真名的欄位都不提供——沒有欄位，就不會有人不小心填進去。
可識別資訊留在附錄 D 的私人檔（`*.private.md`，已排除於版控之外）。
`--code` 限制 4 個字，是為了在打字的當下讓人停一秒。

**二、離站標準寫死在程式裡。**
不放進使用者可改的設定檔，因為那會讓「為了這學期能過而下修標準」變得太容易
（附錄 C 的反模式）。要改標準，就要同時改書——`scripts/check_assets.py` 會比對兩者。

**三、記錄用 JSONL。**
一行一天，任何文字編輯器都能開；append-only，不會被一次誤操作洗掉；
出事時用 `grep` 就能救。家庭的資料保存期是十年以上，格式必須比工具活得久。

**四、ABC 的 A 與 C 不准留白，也不准填「不知道」。**
ABC 最常見的失敗不是記錯，是只記 B（「他今天又鬧了三次」）。
沒有前事與後果，行為就只是一個孤立事件。而「不知道」「突然就」幾乎總是代表
「當時沒看到」——留著它，兩週後這份記錄會完全無法判讀。

**五、ABC 記錄不足 10 筆時，`function` 不給結論。**
第 35 章要求連續兩週、至少 10 筆。低於門檻時給出的「功能」，
反映的是最近一次事件的印象——而依印象選策略，正是這一章要避免的事。

---

## 開發

```bash
make check     # ruff + mypy strict + pytest（覆蓋率門檻 85%）—— 需要 dev 依賴
python3 selftest.py   # 零依賴煙霧測試 —— 什麼都不用裝
```

`selftest.py` 不是 `pytest` 套件的替代品，而是給「電腦上沒有 pip」的讀者用的。
CI 兩者都跑。

> ⚠️ 本工具不提供任何醫療建議。`redflags` 顯示的清單是**就醫時機的提醒**，
> 不是診斷依據；所有用藥與檢查決定，一律由主治醫師判斷。
