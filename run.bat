@echo off
title ADVOCATE Multi-Agent SDLC Launcher
echo ==========================================================
echo   ADVOCATE // Autonomous Multi-Agent SDLC System Launcher
echo ==========================================================
echo.
echo Verifying Python runtime and starting FastAPI server...
echo.
echo Application url: http://localhost:8000
echo.
uv run backend/main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to run backend/main.py. Ensure 'uv' is installed and in your PATH.
    echo.
)
pause
