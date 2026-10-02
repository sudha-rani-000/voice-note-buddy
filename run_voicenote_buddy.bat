@echo off
title VoiceNote Buddy
cd /d "%~dp0"

echo ========================================================
echo               Starting VoiceNote Buddy
echo ========================================================
echo.

:: Check if virtual environment exists
if not exist ".venv\Scripts\streamlit.exe" (
    echo [ERROR] Virtual environment not found. Please install requirements first.
    pause
    exit /b 1
)

:: Launch Streamlit app
echo [INFO] Launching VoiceNote Buddy at http://localhost:8501 ...
.venv\Scripts\streamlit.exe run app.py
pause
