@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo          LED CNTRL - Setup
echo ========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or newer from python.org and enable "Add Python to PATH".
  pause
  exit /b 1
)
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
py -3 led_cntrl.py
if errorlevel 1 pause
