.PHONY: help build check check-book check-assets check-impl assets pdf mutate mutate-auto ci clean

help:            ## 顯示可用目標
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

build:           ## 重建書本成品(慢車到站.html + 慢車到站_全書.md)
	python3 _build.py

check-book:      ## 書稿:圖片引用 / 簡體字 / 醫療免責 / 去識別化 / 建置同步 / HTML id
	python3 scripts/check_book.py

check-assets:    ## impl 資產:教材編號 / 階段代號 / 指標名 / 列印檔名 / .env 覆蓋率
	python3 scripts/check_assets.py

check-impl:      ## impl Python:ruff + mypy strict + pytest(覆蓋率門檻 85%)
	$(MAKE) -C impl check

assets:          ## 產生列印用資產(檢核卡 / 代幣板 / 字卡 / 四張記錄表)到 impl/out
	$(MAKE) -C impl assets

pdf:             ## 產生 PDF(需 Windows + Chrome;見 BUILD_STANDARD §8)
	@echo "PDF 需在 Windows 端執行 Chrome headless："
	@echo "  cmd.exe /c _make_pdf.bat"
	@echo "（WSL 內無法直接跑 Chrome；腳本已內建 §8 的四個踩雷處理）"

mutate:          ## 變異測試:把已修復的缺陷改回去,驗證測試真的抓得到(慢,數分鐘)
	python3 scripts/mutation_sweep.py

mutate-auto:     ## 機械變異:不看修過什麼,直接翻運算子/常數找沒人在看的行(很慢,僅報告)
	python3 scripts/mutation_sweep.py --auto=120

check: check-book check-assets   ## 不需要 Python 依賴的快速檢查

ci: check check-impl mutate      ## CI 全套(等同 .github/workflows/ci.yml)

clean:           ## 清除建置產物與快取
	rm -rf __pycache__ impl/.pytest_cache impl/.ruff_cache impl/.mypy_cache impl/out
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
