@echo off
REM Run script for Techno-Notes (Windows)

cd /d "%~dp0"

echo === Starting Techno-Notes ===
echo.

REM Check if virtual environment exists
if not exist venv (
    echo Error: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check Python dependencies
python -c "import flask, PyPDF2, requests" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Missing Python dependencies!
    echo Please run setup.bat again
    pause
    exit /b 1
)

REM Show GPU/VRAM info and model recommendation
echo.
echo === Hardware ^& Model Info ===

REM Read current model from config
for /f "delims=" %%i in ('python -c "import json; f=open('llm_config.json'); print(json.load(f).get('model_name','qwen2.5:14b')); f.close()" 2^>nul') do set CURRENT_MODEL=%%i
if "%CURRENT_MODEL%"=="" set CURRENT_MODEL=qwen2.5:14b
echo Current model: %CURRENT_MODEL%

REM Recommended VRAM lookup (in GB)
set REC_VRAM=5
if "%CURRENT_MODEL%"=="mistral-nemo:12b" set REC_VRAM=8
if "%CURRENT_MODEL%"=="qwen2.5:7b" set REC_VRAM=5
if "%CURRENT_MODEL%"=="qwen2.5:14b" set REC_VRAM=10
if "%CURRENT_MODEL%"=="command-r:35b" set REC_VRAM=24

REM Check for NVIDIA GPU
where nvidia-smi >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=1,2,3 delims=," %%a in ('nvidia-smi --query-gpu^=name^,memory.total^,memory.free --format^=csv^,noheader 2^>nul') do (
        set GPU_NAME=%%a
        set VRAM_TOTAL=%%b
        set VRAM_FREE=%%c
    )

    if defined GPU_NAME (
        echo GPU: %GPU_NAME%
        echo VRAM:%VRAM_FREE% /%VRAM_TOTAL% free
        echo Recommended VRAM for %CURRENT_MODEL%: ~%REC_VRAM% GB

        REM Extract free VRAM in MB and convert to GB for comparison
        for /f "delims= " %%x in ("%VRAM_FREE%") do set VRAM_FREE_MB=%%x
        set /a VRAM_FREE_GB=%VRAM_FREE_MB% / 1024

        if %VRAM_FREE_GB% lss %REC_VRAM% (
            echo.
            echo WARNING: Available VRAM ^(~%VRAM_FREE_GB% GB^) is below recommended ^(~%REC_VRAM% GB^).
            echo    Model will partially offload to CPU and run slower.
            echo    Consider using a smaller model ^(e.g. qwen2.5:7b^) for faster results.
        ) else (
            echo [OK] Sufficient VRAM available
        )
    ) else (
        echo [i] nvidia-smi available but no GPU detected
        echo    Models will run on CPU ^(significantly slower^)
    )
) else (
    echo [i] No NVIDIA GPU detected -- models will run on CPU ^(slower^)
    echo    Recommended VRAM for %CURRENT_MODEL%: ~%REC_VRAM% GB
)

echo.
echo ================================
echo.

REM Run the application
echo Starting application...
echo.
python app.py
