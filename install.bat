@echo off
echo ============================================
echo   QA Team ViewClipper - Installation
echo ============================================
echo.

cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists, skipping...
)

echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/3] Installing dependencies...
pip install -r requirements.txt -q

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies!
    echo Try running manually:
    echo   pip install pywin32 pillow google-api-python-client google-auth-httplib2 google-auth-oauthlib
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo To start ViewClipper:
echo   - Double-click run.bat
echo   - Or run: python main.py
echo.
echo Default hotkeys:
echo   Alt+S     = Full screen capture
echo   Alt+R     = Region capture
echo   Ctrl+P    = Settings
echo   Ctrl+C    = Quit
echo.
pause
