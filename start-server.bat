@echo off
cd /d "%~dp0"
set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
echo Starting local YouTube downloader server...
if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" server.py
) else (
  py -3.14 server.py
  if errorlevel 1 (
    echo.
    echo Python 3.14 was not found. Please install Python 3.14 or update the path in this batch file.
    pause
    exit /b 1
  )
)
