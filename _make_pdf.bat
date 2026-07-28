@echo off
rem ============================================================
rem  慢車到站 - PDF 產生（Chrome headless）
rem  系列標準 BUILD_STANDARD.md §8。四個踩雷已經內建，照跑即可。
rem
rem  用法（在 Windows 命令提示字元，或從 WSL 呼叫 cmd.exe /c）：
rem      _make_pdf.bat
rem
rem  前置：先跑過 python _build.py，確認 慢車到站.html 是最新的。
rem ============================================================

setlocal

rem --- 依你的環境調整這一行 ---
set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME%" (
  echo [X] 找不到 Chrome：%CHROME%
  echo     請修改本檔第 12 行的 CHROME 路徑。
  exit /b 1
)
if not exist "慢車到站.html" (
  echo [X] 找不到 慢車到站.html，請先執行：python _build.py
  exit /b 1
)

rem ── 踩雷 3：CJK 檔名先複製成 ASCII 暫存再印，印完改回 ──
rem  Chrome 對非 ASCII 路徑的處理在部分版本上會靜默失敗。
copy /y "慢車到站.html" "_slowtrain_tmp.html" >nul

rem ── 踩雷 1：一定要用 --headless=new（舊的 --headless 已成 no-op，會印出空檔）──
rem ── 踩雷 2：每檔獨立 user-data-dir，且放在可寫目錄；共用 profile 會撞鎖靜默失敗 ──
rem ── 加渲染等待旗標，否則新 headless 會在渲染完成前就印 → 空白 ──
echo [1/3] 產生 PDF（約需 20-40 秒，請勿關閉視窗）...
"%CHROME%" --headless=new --disable-gpu ^
  --run-all-compositor-stages-before-draw ^
  --virtual-time-budget=15000 ^
  --no-pdf-header-footer ^
  --user-data-dir="%TEMP%\slowtrain_udd" ^
  --print-to-pdf="_slowtrain_tmp.pdf" ^
  "_slowtrain_tmp.html"

rem ── 踩雷 4：Chrome headless 是 async detach 寫檔，launch 後要等它寫完。 ──
rem  不要用 timeout /t —— 從 WSL 經 cmd.exe 呼叫時 stdin 被重導向，timeout 會立即結束。
echo [2/3] 等待寫檔完成...
ping -n 26 127.0.0.1 >nul

if not exist "_slowtrain_tmp.pdf" (
  echo [X] PDF 沒有產生。常見原因：
  echo     - Chrome 版本較舊，不支援 --headless=new
  echo     - user-data-dir 不可寫
  del "_slowtrain_tmp.html" >nul 2>&1
  rmdir /s /q "%TEMP%\slowtrain_udd" >nul 2>&1
  exit /b 1
)

echo [3/3] 收尾...
move /y "_slowtrain_tmp.pdf" "慢車到站.pdf" >nul
del "_slowtrain_tmp.html" >nul 2>&1
rmdir /s /q "%TEMP%\slowtrain_udd" >nul 2>&1

for %%A in ("慢車到站.pdf") do set SIZE=%%~zA
set /a SIZE_MB=%SIZE%/1048576
echo.
echo [OK] 已產生 慢車到站.pdf（約 %SIZE_MB% MB）
echo.
echo 正常大小參考：純文字書約 14-16 MB；含整頁封面海報的圖多書約 30 MB。
echo 若超過 100 MB，代表是手動 Ctrl+P 並勾了「背景圖形」——那會把 CSS 漸層點陣化。
echo 請一律用這支腳本，不要手動列印。
endlocal
