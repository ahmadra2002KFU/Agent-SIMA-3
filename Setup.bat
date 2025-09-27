@echo off
echo ========================================
echo AI Sima Chatbot - Setup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo Python found. Checking version...
python -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"

REM Check if we're in the correct directory
if not exist "server\app.py" (
    echo ERROR: Please run this script from the Agent3 project root directory
    echo The script should be in the same folder as the 'server' directory
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...
python -m venv .venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing required dependencies...
echo This may take a few minutes...

REM Install core dependencies
pip install fastapi uvicorn[standard]
if %errorlevel% neq 0 (
    echo ERROR: Failed to install FastAPI and Uvicorn
    pause
    exit /b 1
)

REM Install data processing libraries
pip install pandas openpyxl numpy
if %errorlevel% neq 0 (
    echo ERROR: Failed to install data processing libraries
    pause
    exit /b 1
)

REM Install visualization libraries
pip install plotly
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Plotly
    pause
    exit /b 1
)

REM Install HTTP client libraries
pip install aiohttp requests
if %errorlevel% neq 0 (
    echo ERROR: Failed to install HTTP client libraries
    pause
    exit /b 1
)

REM Install additional utilities
pip install aiofiles websockets python-multipart
if %errorlevel% neq 0 (
    echo ERROR: Failed to install additional utilities
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Download and install LM Studio from https://lmstudio.ai/
echo 2. Load a compatible model in LM Studio
echo 3. Start LM Studio server on port 1234
echo 4. Run 'Run.bat' to start the application
echo.
echo Press any key to exit...
pause >nul
