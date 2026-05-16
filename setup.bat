@echo off
REM Startup script for Continual RAG Agent on Windows

echo Continual RAG Agent - Startup
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.9+
    exit /b 1
)

REM Check if Node.js is installed
npm --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js/npm not found. Please install Node.js 18+
    exit /b 1
)

echo Python found: %python%
echo Node.js found: %npm%
echo.

REM Set Groq API Key (modify this or set as environment variable)
if "%GROQ_API_KEY%"=="" (
    echo Warning: GROQ_API_KEY not set. Please set it as environment variable:
    echo set GROQ_API_KEY=your_key_here
    echo.
)

REM Install backend dependencies
echo Installing backend dependencies...
cd backend
pip install -r requirements.txt -q
cd ..

REM Install frontend dependencies
echo Installing frontend dependencies...
cd frontend
npm install -q
cd ..

REM Build instructions
echo.
echo ================================
echo Setup complete! To run the system:
echo.
echo Terminal 1 - Backend:
echo   cd backend
echo   set GROQ_API_KEY=your_key_here
echo   python main.py
echo.
echo Terminal 2 - Frontend:
echo   cd frontend
echo   npm run dev
echo.
echo Then open your browser to http://localhost:5173
echo ================================
