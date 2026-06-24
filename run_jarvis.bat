@echo off
title J.A.R.V.I.S.

:: Set UTF-8 encoding to prevent Unicode/emoji crashes on Windows
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

echo.
echo  Starting J.A.R.V.I.S...
echo.

:: Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo  [WARNING] Virtual environment not found. Run setup.bat first.
    echo  Attempting to run with system Python...
)

:: Set Hugging Face token to avoid rate limiting on model downloads
set HF_TOKEN=""

:: Run Jarvis — must be launched as Administrator for some features
:: (keyboard hotkey listener requires elevated privileges on some systems)
python -m backend.main

if errorlevel 1 (
    echo.
    echo  [ERROR] Jarvis exited with an error. Check jarvis.log for details.
    pause
)
