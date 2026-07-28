# 系列製作標準 · Book Build Standard

> **這份文件在系列各書中內容一致（《開源器識》《代碼壁壘》《代理覺醒》《除錯專家》《慢車到站》）。**
> 任何新書要 align 系列任一本，照這份做即可——**只改常數與內容，不要自己另立一套**（不要改 CSS / Markdown 解析器 / 封面邏輯）。
> 工具鏈源頭：`D:/GameDevZ/gs2/docs/book` 的 `_build.py`（同一套 CSS / 解析器）。

---

## 0. 一句話原則
所有書、所有語言版本**共用同一支 `_build.py`**（同一份 CSS、Markdown 解析器、封面邏輯）。每本書 / 每語言只改頂部「常數區」與少數在地化 regex，其餘一字不動。

---

## 1. 目錄結構
```
<BookRoot>/
  00_序言.md  01_*.md … NN_*.md        # 繁體正文（每檔一章或一篇，H1 為該章/篇標題）
  附錄A_*.md … 附錄Z_*.md               # 繁體附錄
  <Cover>.png                           # 封面海報（直式；書名/副標/命題已燒進圖內）
  _build.py                             # 繁體建置腳本（標準版）
  _convert_cn.py                        # 繁→簡，並自動產生 cn/_build.py
  index.html                            # 多語落地頁
  README.md   LICENSE   BUILD_STANDARD.md
  <BookTitle>.html  <BookTitle>_全書.md  <BookTitle>.pdf   # 繁體成品
  cn/   # 简体：轉換後 .md + cn/_build.py + 代码…（简）成品
  en/   # English：翻譯後 .md + en/_build.py + <BookTitle>.html/_full.md/.pdf
  ja/   # 日本語：翻訳後 .md + ja/_build.py + 成品
```
**root = 繁體主版**；`cn/` `en/` `ja/` 各為一個語言版，各自有一支 `_build.py`。

---

## 2. 共用 `_build.py`：只准改「常數區」
每語言 `_build.py` 的差異**僅限**：
| 要改 | 說明 |
|------|------|
| `BOOK_TITLE` `BOOK_SUB` | 書名、副標（在地化） |
| `OUTFILE` | **非中文版**才有；Latin 檔名，如 `"TheCodeBarrier"`（輸出 `TheCodeBarrier.html/_full.md`） |
| `COVER_CANDIDATES` | 封面檔名候選，如 `["<Book>.png","cover.png"]` |
| `title_for()` / `part_for()` 的 regex | 在地化：序/Preface/序、第N章/Chapter N/第N章、附錄/Appendix X/付録X、第N篇/Part … |
| `build_merged()` 合併版引言 | 一句書籍簡介 |

**其餘全部共用、禁止改**：CSS、`inline()`/`md_to_html()` 解析器（含 `~~~```~~~ 程式碼區塊、表格、`> 💡/🔍/⚠️` 框、清單、圖片）、`cover_section()`、`order()`、`build_html()`。

---

## 3. 封面規範（image-only 海報）
- 封面是**一整張設計好的資訊圖海報**（書名、副標、核心命題都已在圖裡）。**HTML 封面頁只放這張圖，不再另放標題/副標文字**（避免重複）。
- 機制：`cover_path()` 從 `COVER_CANDIDATES` 找圖 → `cover_section()` 內嵌。**依副檔名分兩條路**：
  - **`.png` / `.jpg`**：**base64 內嵌**成 `<figure class="cover"><img src="data:image/png;base64,…"/></figure>`。
  - **`.svg`**：**直接內嵌原生 `<svg>` 標記**，包一層 `<div class="svgwrap">`
    （`<figure class="cover"><div class="svgwrap"><svg …></svg></div></figure>`）。
    向量不受縮放失真、體積遠小於等效 PNG，且同樣零外部資源。架構圖（`diagrams/*.svg`）走同一條路，
    差別只在外層是 `figure.plate`（`max-width:820px`）而非 `figure.cover`。
- CSS 固定：`figure.cover img` 與 `figure.cover .svgwrap svg` 皆 `width:100%;max-width:680px` —— **680px，勿改**。
- **全書自帶、可離線**：0 外部資源（不得有 CDN / 外連 CSS / JS / 字型 / 圖；點陣圖一律 base64、向量圖一律原生內嵌）。

> 《除錯專家》採 SVG 封面 + 16 張架構圖；《慢車到站》採 SVG 封面 + 20 張流程圖，並沿用《代理覺醒》的情境驅動架構（第七篇）。兩種都合規，**但同一本書內
> 封面與架構圖應一致**，別一半 PNG 一半 SVG。

### 3.1 SVG 內嵌必須做 id 命名空間化（**新增規範，全系列適用**）

多張 SVG 被**原生內嵌進同一份 HTML** 時，它們各自 `<defs>` 裡的 `id`（marker／filter／
gradient）會落進同一個全域命名空間。HTML 規定 id 唯一，`url(#箭頭)` 只會解析到**文件順序
中的第一個**——也就是封面的那一份。

這件事的惡劣之處在於它**不會報錯**：若各檔的定義碰巧相同（《除錯專家》17 張圖的
`箭頭`/`紅箭頭`/`光暈`/`陰影` 就是逐字相同），渲染完全正常，你不會發現有問題；直到某天有人
只改了其中一張圖的箭頭顏色，那個改動被靜默忽略——而他單獨打開那張 `.svg` 又一切正常。

因此 `_build.py` 的 `svg_or_img()` 與 `cover_section()` **必須**在內嵌當下呼叫
`namespace_svg_ids(svg, prefix)`，把該檔所有 `id=` 與 `url(#…)`／`href="#…"` 引用加上檔名
前綴（`cover-箭頭`、`d05_supervisor_workers-箭頭`…）。源 SVG 不必改，繪圖者也不需要自己
避開撞名。驗收方式：建置後的 HTML 內 `id` 必須零重複（`scripts/check_book.py` 已納入檢查）。

---

## 4. 檔名慣例（決定順序的是「數字前綴」）
- **繁體 root**：`00_序言.md`、`NN_*.md`（章/篇）、`附錄X_*.md`。`order()` 依序 glob：`00_*` → `01..49_*` → `附錄*_*`。
- **en / ja 沒有「附錄」二字**：附錄改成**編號續檔**接在章節後，例如
  `12_appendix_a_*.md`、`13_appendix_b_*.md`……讓單一 `NN_*` glob 依序收錄（en/ja 的 `order()` 會**移除** `附錄*` 那段）。
- 各語言檔名可在地化（en 用英文 slug、ja 用日文/羅馬字），但**編號前綴一致決定閱讀順序**。

---

## 5. 建置流程（每語言各跑一次）
```bash
python _build.py     # 產 <Title>.html（側欄目錄）＋ <Title>_全書/_full.md
```
- 在 root 跑 → 繁體成品；在 `cn/`、`en/`、`ja/` 各 `cd` 進去跑一次。
- （WSL 若 python3 無 pip / 模組，改用 Windows python：`cmd.exe /c "python <路徑>\_build.py"`。）

---

## 6. 简体版 `cn/`：`_convert_cn.py`（機械轉換，非翻譯）
- 需要 **OpenCC**（`opencc.OpenCC('tw2sp')`，含台灣→大陸用語）。WSL 無 pip 時用 **Windows python**（多半已裝 opencc）。
- 額外處理 OpenCC 不轉的台灣代名詞：`EXTRA = {'牠':'它','妳':'你','祂':'它'}`。
- 動作：轉全部 root `.md` → `cn/`，並把 `_build.py` **一併簡體化**成 `cn/_build.py`，複製封面。
- 之後 `cd cn && python _build.py`。

---

## 7. `index.html` 多語落地頁（共用模板）
結構：`header`（書名 / EN 標題 / 副標）＋ `hero`（封面縮圖 + 命題金句框）＋ 語言卡片。
- 每個語言一張 `.card`，連到該語 `.html`，附「章數/篇數・側欄目錄・規模」meta。
- 尚未完成的語言用 `.card.soon`（半透明 `opacity:.62`）。
- **只改文字與連結**，版面沿用。

---

## 8. PDF：Chrome headless `--print-to-pdf`
各語 HTML 用 **Chrome headless** 列印（**不是** 手動 Ctrl+P）。踩雷（照做才正常）：
1. **用 headless，別手動 Ctrl+P**：手動勾「背景圖形」會把 CSS 漸層點陣化，暴漲到 100MB+（最大的雷）。
2. **一次只印一個檔、每檔獨立 `--user-data-dir`**：共用 profile 撞鎖／singleton 靜默失敗。UDD 用可寫目錄（`%TEMP%\xx` 或專案內，**別用 `C:\Windows\Temp`**），印完清掉。
3. **CJK 檔名先複製成 ASCII 暫存**再印，印完改回中文名（`en/ja` 本就 ASCII）。

**★ 2026 現行 Chrome 兩個修正（sister READMEs 的舊指令已過時，務必照這個）**：
- 舊 `--headless` 已被移除、變 no-op（印出空檔）。**要用 `--headless=new`**，且**必加渲染等待旗標**，否則新 headless 會在渲染完成前就印 → 空白：
  `--headless=new --disable-gpu --run-all-compositor-stages-before-draw --virtual-time-budget=15000 --no-pdf-header-footer`
- **從 WSL 經 `cmd.exe` 跑 bat 時 `timeout /t` 會失效**（stdin 被重導向 →「不支援將輸入重新導向」立即結束、完全不等）。**改用 `ping -n <秒+1> 127.0.0.1 >nul` 當 sleep**；且 chrome headless 是 **async detach 寫檔**，launch 後要等 **~20 秒**讓它寫完再檢查／印下一檔。

**★ 2026-07 又踩到的兩個（《慢車到站》實測）**：
5. **`.bat` 檔必須是純 ASCII**。`cmd.exe` 用系統 ANSI 頁碼（台灣是 cp950）解析 `.bat`，
   一個含中文的 UTF-8 批次檔會整個變成亂碼——而最惡劣的是 `if exist "中文檔名"` 會
   **靜默判為不存在**然後走進錯誤分支。做法：批次檔全英文，中文檔名由呼叫端（Makefile／WSL）
   複製成 ASCII 暫存再傳進去。
6. **Chrome 150 會 exit 0 但不產生檔案**；同核心的 **Edge 可以**。
   因此腳本應該**先試 Edge、再試 Chrome**。另外 `--virtual-time-budget=15000` 對
   「900 KB HTML + 21 張內嵌 SVG」不夠，實測要 **60000**，且 launch 後要等 **60 秒**再檢查。

《慢車到站》已把上述六個踩雷寫成可直接執行的 `_make_pdf.bat`（含 ASCII 暫存改名、
獨立 user-data-dir、`ping` 當 sleep、以及產出大小的自我檢查）——新書可直接複製該檔改常數。

可用範例（每檔一段；bat 存 CRLF）：
```bat
%CHROME% --headless=new --disable-gpu --run-all-compositor-stages-before-draw ^
  --virtual-time-budget=15000 --no-pdf-header-footer ^
  --user-data-dir="%TEMP%\udd_1" --print-to-pdf="out.pdf" "src.html"
ping -n 22 127.0.0.1 >nul
```
正常大小：純文字書約 14–16 MB；**含整頁封面海報的圖多書約 30 MB**（皆正常；>100MB 才是背景點陣化的雷）。

---

## 9. 對齊新書 SOP（照抄，別發明）
1. 從系列任一本 copy：`_build.py`、`_convert_cn.py`、`index.html`、`BUILD_STANDARD.md`（本檔）。
2. **只改常數區**：`BOOK_TITLE` / `BOOK_SUB` / `OUTFILE`（非中文版）/ `COVER_CANDIDATES` / `title_for`·`part_for` 在地化 regex / 合併引言。
3. 內容 `.md` 照 §4 檔名慣例放好；放一張封面海報 PNG（檔名列進 `COVER_CANDIDATES`）。
4. `python _build.py` 建繁體 → `_convert_cn.py` 產简 → 翻譯 `en/`·`ja/` 後各自 build → 補 `index.html` → 印 PDF。

> **鐵律：只改「常數」與「內容」，不要改 CSS / 解析器 / 封面邏輯 / 目錄結構——不要自己弄一套。**
