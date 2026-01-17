@echo off
REM Setup script for Enhanced LinkedIn Job Scraper (Windows)

echo ========================================
echo Enhanced LinkedIn Job Scraper - Setup
echo ========================================
echo.

REM Check Python installation
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

REM Create virtual environment (optional but recommended)
echo [2/5] Do you want to create a virtual environment? (Recommended)
set /p createvenv="Create venv? (y/n): "
if /i "%createvenv%"=="y" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Virtual environment created and activated
) else (
    echo Skipping virtual environment creation
)
echo.

REM Install required packages
echo [3/5] Installing required packages...
pip install --upgrade pip
pip install requests beautifulsoup4 selenium webdriver-manager
echo.

REM Create required directories
echo [4/5] Creating required directories...
if not exist "backup" mkdir backup
if not exist "logs" mkdir logs
echo Directories created
echo.

REM Check for existing files
echo [5/5] Checking for existing files...
if exist "job_bot_edited.py" (
    echo [OK] Found job_bot_edited.py
) else (
    echo [WARNING] job_bot_edited.py not found!
    echo Please make sure your original scraper file is named job_bot_edited.py
)

if exist "config.json" (
    echo [OK] Found config.json
) else (
    echo [INFO] config.json will be created on first run
)
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Make sure all module files are in the same folder:
echo    - main.py
echo    - database.py
echo    - reports.py
echo    - scraper.py
echo    - job_bot_edited.py (your original scraper)
echo.
echo 2. Update config.json with your credentials
echo.
echo 3. Run the scraper:
if /i "%createvenv%"=="y" (
    echo    venv\Scripts\activate
)
echo    python main.py
echo.
echo Press any key to exit...
pause >nul