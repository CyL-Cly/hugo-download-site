@echo off
setlocal
set HUGO_EXE=%~dp0.tools\hugo\hugo.exe
if not exist "%HUGO_EXE%" (
  echo Hugo binary not found at %HUGO_EXE%
  echo Extract hugo_0.169.0_windows-amd64.zip into .tools\hugo\ first.
  exit /b 1
)
echo [1/4] Generating QR codes for mobile-app resources...
python "%~dp0tools\gen_qr.py" || echo       WARN: QR generation failed, build continues
echo [2/4] Building site...
"%HUGO_EXE%" --source "%~dp0." --destination "%~dp0public" --minify --cleanDestinationDir
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)
echo [3/4] Generating GEO artifacts (llms.txt, sitemap.md, Markdown mirrors)...
python "%~dp0tools\gen_geo.py"
if errorlevel 1 (
  echo GEO generation failed.
  exit /b 1
)
echo [4/4] Submitting URLs to IndexNow (Bing)...
python "%~dp0tools\indexnow.py" || echo       WARN: IndexNow submission failed, build continues
echo Build done. Now: git add -A ^&^& git commit -m "update site" ^&^& git push
endlocal
exit /b 0
