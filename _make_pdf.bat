@echo off
rem ============================================================
rem  Print an HTML file to PDF via a Chromium browser, headless.
rem  BUILD_STANDARD.md section 8.
rem
rem  Usage:  _make_pdf.bat <input.html> <output.pdf>
rem  Both arguments should be ASCII paths (see gotcha 5 below).
rem
rem  Gotchas handled here (all of them cost real debugging time):
rem   1. --headless=new is required; the old --headless is a no-op
rem      and silently prints an empty file.
rem   2. Per-run --user-data-dir in a writable place. A shared
rem      profile hits a lock and fails silently.
rem   3. CJK filenames: pass ASCII paths, rename afterwards.
rem   4. Chrome detaches and writes asynchronously. Do NOT use
rem      "timeout /t": when invoked from WSL its stdin is
rem      redirected and it returns immediately. Use ping instead.
rem   5. THIS FILE MUST STAY ASCII-ONLY. cmd.exe parses .bat with
rem      the system ANSI codepage, so a UTF-8 .bat containing
rem      Chinese turns into mojibake and IF EXIST tests fail.
rem   6. Chrome 150 exits 0 but produces no file. Edge (same
rem      Chromium core) works. So: try Edge first, Chrome second.
rem      Also give a generous --virtual-time-budget: a 900 KB
rem      HTML with 21 inlined SVGs needs far more than 15s.
rem ============================================================

setlocal

set "BROWSER="
set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
set "EDGE64=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "CHROME86=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

if exist "%EDGE%" set "BROWSER=%EDGE%"
if not defined BROWSER if exist "%EDGE64%" set "BROWSER=%EDGE64%"
if not defined BROWSER if exist "%CHROME%" set "BROWSER=%CHROME%"
if not defined BROWSER if exist "%CHROME86%" set "BROWSER=%CHROME86%"

set "SRC=%~f1"
set "DST=%~f2"

if not defined BROWSER (
  echo [X] No Chromium browser found. Edit the paths in this file.
  exit /b 1
)
if not exist "%SRC%" (
  echo [X] Input not found: %SRC%
  exit /b 1
)
if exist "%DST%" del /q "%DST%"

echo [1/2] Printing with: %BROWSER%
echo       %SRC%
"%BROWSER%" --headless=new --disable-gpu --no-sandbox ^
  --run-all-compositor-stages-before-draw ^
  --virtual-time-budget=60000 ^
  --no-pdf-header-footer ^
  --user-data-dir="C:\Users\Public\_pdf_udd" ^
  --print-to-pdf="%DST%" ^
  "file:///%SRC:\=/%" >nul 2>&1

echo [2/2] Waiting for the async write to finish...
ping -n 61 127.0.0.1 >nul
rmdir /s /q "C:\Users\Public\_pdf_udd" >nul 2>&1

if not exist "%DST%" (
  echo [X] No PDF produced.
  echo     Try: another Chromium browser, or a longer virtual-time-budget.
  exit /b 1
)
for %%A in ("%DST%") do echo [OK] %DST% - %%~zA bytes
echo      Reference: text-only book 14-16 MB; image-heavy with a full-page
echo      cover poster around 25-30 MB. Over 100 MB means someone printed
echo      manually with "background graphics" on - never do that.
endlocal
