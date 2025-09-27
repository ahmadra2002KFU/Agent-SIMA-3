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
echo Checking if LM Studio is running...
curl -s http://127.0.0.1:1234/v1/models >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: LM Studio does not appear to be running on port 1234
    echo The application will still start but AI features may not work
    echo.
    echo To fix this:
    echo 1. Start LM Studio
    echo 2. Load a model
    echo 3. Start the local server on port 1234
    echo.
    echo Press any key to continue anyway...
    pause >nul
    echo.
)

echo Starting AI Sima Chatbot server...
echo Server will be available at: http://localhost:8010
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server and open browser
start "" "http://localhost:8010"
cd server
uvicorn app:app --host 127.0.0.1 --port 8010

REM If we get here, the server stopped
echo.
echo Server stopped.
pause
