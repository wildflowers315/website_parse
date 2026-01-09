@echo off
REM Quick activation script for the virtual environment
echo Activating Python virtual environment...
call .venv\Scripts\activate.bat
echo.
echo ========================================
echo Environment activated!
echo ========================================
echo.
echo To run the extraction script:
echo   python extract_content.py
echo.
echo To deactivate:
echo   deactivate
echo.
