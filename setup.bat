@echo off
echo =========================================
echo  Government Truth Portal - Setup Script
echo  Microsoft Imagine Cup 2025
echo =========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found

REM Navigate to backend
cd backend

REM Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)
echo [OK] Virtual environment ready

REM Activate virtual environment
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated

REM Install dependencies
echo [INFO] Installing Python dependencies...
pip install -r requirements.txt --quiet
echo [OK] Dependencies installed

REM Create .env if not exists
if not exist ".env" (
    echo [INFO] Creating .env file from template...
    copy .env.example .env
    echo [IMPORTANT] Please edit backend\.env and add your API keys!
    echo.
    echo API Keys needed:
    echo   1. Gemini API: https://aistudio.google.com
    echo   2. Azure Document Intelligence: Azure Portal
    echo   3. Azure AI Search: Azure Portal
    echo   4. Azure Translator: Azure Portal
    echo.
)

REM Create data directories
if not exist "data\documents" mkdir data\documents
echo [OK] Data directories created

echo.
echo =========================================
echo  Setup Complete!
echo =========================================
echo.
echo Next steps:
echo   1. Edit backend\.env with your API keys
echo   2. Run: cd backend ^&^& python main.py
echo   3. Open index.html in a browser
echo.
pause
