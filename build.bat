@echo off
echo ============================================
echo   QA Team ViewClipper - Build Script
echo ============================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo [1/4] Installing dependencies...
pip install -r requirements.txt -q

echo [2/4] Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo [3/4] Building executable with PyInstaller...
pyinstaller ViewClipper.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo [4/4] Build complete!
echo.
echo ============================================
echo   OUTPUT: dist\ViewClipper.exe
echo ============================================
echo.
echo Next steps to create installer:
echo   1. Download Inno Setup from: https://jrsoftware.org/isdl.php
echo   2. Install Inno Setup
echo   3. Open ViewClipper_Installer.iss with Inno Setup
echo   4. Click Build ^> Compile (or press Ctrl+F9)
echo   5. Installer will be in: installer_output\
echo.
pause
