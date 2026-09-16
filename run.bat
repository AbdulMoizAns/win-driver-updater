@echo off
title Windows Driver Updater
cd /d "%~dp0"

:: 1. Self-elevation check (Run as Administrator for full driver permissions)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [i] Requesting Administrator permissions...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

:: 2. Locate Python executable
set "PYTHON_BIN="

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_BIN=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :RUN
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_BIN=python"
    goto :RUN
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_BIN=py -3"
    goto :RUN
)

echo.
echo ========================================================
echo [!] Python 3.10+ was not found on your system!
echo Please install Python from https://www.python.org/
echo ========================================================
echo.
pause
exit /b 1

:RUN
echo ========================================================
echo        Starting Windows Driver Updater (Admin)...
echo ========================================================
"%PYTHON_BIN%" main.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Application exited with code: %errorlevel%
    pause
)
