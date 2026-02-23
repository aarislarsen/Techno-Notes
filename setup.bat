@echo off
REM setup.bat - Automated setup script for Techno-Notes (Windows)

echo === Techno-Notes - Automated Setup (Windows) ===
echo.

REM Check Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Python is not installed or not in PATH.
    echo     Please install Python 3.7+ from https://www.python.org/downloads/
    echo     Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Show Python version
echo [i] Found Python:
python --version

REM Verify Python version >= 3.7
python -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Python 3.7 or higher is required.
    pause
    exit /b 1
)
echo [OK] Python version is sufficient

REM Go to script directory
cd /d "%~dp0"
echo [i] Application directory: %CD%

REM Create virtual environment
echo.
echo [->] Creating Python virtual environment...
if exist venv (
    echo [i] Virtual environment already exists, skipping creation
) else (
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [X] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo [->] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [->] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel --quiet
echo [OK] pip upgraded

REM Install dependencies
echo [->] Installing Python packages...
pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [X] Failed to install Python dependencies
    pause
    exit /b 1
)
echo [OK] Python dependencies installed

REM Create directories
echo [->] Creating application structure...
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs
if not exist logs mkdir logs
if not exist word_templates mkdir word_templates
echo [OK] Application structure created

REM Check Ollama
echo.
echo [->] Checking Ollama installation...
where ollama >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Ollama is installed
    ollama --version 2>nul
) else (
    echo [i] Ollama is not installed.
    echo     Please download and install Ollama from:
    echo     https://ollama.com/download/windows
    echo.
    echo     After installing, restart this setup or run run.bat
)

REM Verify dependencies
echo.
echo [->] Verifying installation...
python -c "import flask, PyPDF2, requests, docx; print('OK')" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Dependency verification failed
    pause
    exit /b 1
)
echo [OK] Python dependencies verified

REM Summary
echo.
echo =========================================
echo [OK] Setup Complete!
echo =========================================
echo.
echo [OK] Virtual environment configured
echo [OK] Python dependencies installed
where ollama >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Ollama installed and ready
) else (
    echo [i] Ollama installation pending - see instructions above
)
echo.
echo [->] To start the application:
echo     run.bat
echo.
echo [->] Then open: http://localhost:5000
echo.

set /p REPLY="Start the application now? (y/n) "
if /i "%REPLY%"=="y" (
    echo [i] Starting application...
    echo.
    call run.bat
)
