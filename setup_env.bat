@echo off
REM Setup script for Python environment using uv
echo ========================================
echo Setting up Python environment with uv
echo ========================================

REM Check if uv is installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo uv is not installed. Installing uv...
    echo.
    REM Install uv using pip (Python's package installer)
    pip install uv
    if %errorlevel% neq 0 (
        echo Failed to install uv. Please install it manually:
        echo   pip install uv
        echo Or download from: https://github.com/astral-sh/uv
        exit /b 1
    )
)

echo.
echo Creating virtual environment with uv...
uv venv

echo.
echo Installing dependencies...
uv pip install -r requirements.txt

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To activate the virtual environment:
echo   .venv\Scripts\activate
echo.
echo To run the extraction script:
echo   python extract_content.py
echo.
