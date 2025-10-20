@echo off
echo ========================================
echo AI Sima Chatbot - Run Script
echo ========================================
echo.

REM Check if we're in the correct directory
if not exist "server\app.py" (
    echo ERROR: Please run this script from the Agent3 project root directory
    echo The script should be in the same folder as the 'server' directory
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run Setup.bat first to install dependencies
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo Using Groq API with Kimi K2 model...
echo No local LM Studio required!

echo Starting Gen-SIMA Chatbot server...
echo Server will be available at: http://localhost:8010
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server and open browser
if "%1"=="--no-open" (
    echo Skipping browser auto-open
) else (
    start "" "http://localhost:8010"
)
cd server
uvicorn app:app --host 127.0.0.1 --port 8010

REM If we get here, the server stopped
echo.
echo Server stopped.
pause
