@echo off
cd /d "%~dp0"
echo Starting local YouTube downloader server...
py -3.14 server.py
if errorlevel 1 (
  echo.
  echo If py failed, trying python...
  python server.py
)
pause
