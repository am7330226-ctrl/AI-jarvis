@echo off
title Jarvis Setup
echo.
echo  ============================================================
echo   J.A.R.V.I.S. — Dependency Installer
echo  ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Download Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo  [1/3] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo  [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo  [3/3] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo  ============================================================
echo   Setup complete!
echo.
echo   NEXT STEPS:
echo   1. Create a .env file or open backend\config.py
echo   2. Set your GEMINI_API_KEY
echo      (Get one free at: https://aistudio.google.com/apikey)
echo   3. Run Jarvis: run_jarvis.bat
echo  ============================================================
echo.
pause
