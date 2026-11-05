@echo off
setlocal
set HUGO_EXE=%~dp0.tools\hugo\hugo.exe
if not exist "%HUGO_EXE%" (
  echo Hugo binary not found at %HUGO_EXE%
  echo Extract hugo_0.169.0_windows-amd64.zip into .tools\hugo\ first.
  exit /b 1
)
"%HUGO_EXE%" --source "%~dp0." --destination "%~dp0public" --minify --cleanDestinationDir
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)
echo Build done. Now: git add -A ^&^& git commit -m "update site" ^&^& git push
endlocal
