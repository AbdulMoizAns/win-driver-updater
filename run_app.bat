@echo off
title Windows Driver Updater
cd /d "%~dp0"

echo ========================================================
echo        Starting Windows Driver Updater...
echo ========================================================

:: 1. Try local user installed Python 3.12
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" main.py
    if %errorlevel% neq 0 pause
    exit /b
)

:: 2. Try standard python in PATH
where python >nul 2>nul
if %errorlevel% equ 0 (
    python main.py
    if %errorlevel% neq 0 pause
    exit /b
)

:: 3. Try py launcher
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 main.py
    if %errorlevel% neq 0 pause
    exit /b
)

echo [!] Python 3.10+ was not found on your system.
echo Please install Python from https://www.python.org/downloads/
pause
