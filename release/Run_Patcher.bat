@echo off
title Unlimited Ammo - Patcher
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup, then run this again.
    pause
    exit /b 1
)

echo Unlimited Ammo - rebuilds the mod from your installed game files.
echo Close the game before continuing.
echo.
echo   1. Unlimited reserve ammo (you still reload)
echo   2. Unlimited ammo, no reload
echo   3. Ammo off (grenades only)
echo   4. Uninstall everything
echo.
choice /c 1234 /n /m "Choose 1-4: "
set pick=%errorlevel%

if %pick%==4 (
    python build_mod.py --uninstall
    pause
    exit /b
)
if %pick%==1 set mode=reserve
if %pick%==2 set mode=no-reload
if %pick%==3 set mode=none

set grenades=
choice /c yn /m "Also unlimited grenades"
if %errorlevel%==1 set grenades=--grenades

python build_mod.py --install %mode% %grenades%
echo.
pause
