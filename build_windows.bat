@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
py -3 -m PyInstaller --noconfirm --clean --windowed --name "LED CNTRL" --collect-all PySide6 led_cntrl.py
echo.
echo Build output: dist\LED CNTRL\LED CNTRL.exe
echo This creates a folder-based Windows app. Use the Inno Setup script to create an installer.
pause
