#!/bin/bash
# Setup and run the Continual RAG Agent system

echo "Starting Continual RAG Agent..."
echo "================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
if ! command_exists python; then
    echo "Error: Python not found. Please install Python 3.9+"
    exit 1
fi

# Check Node.js
if ! command_exists npm; then
    echo "Error: Node.js/npm not found. Please install Node.js 18+"
    exit 1
fi

echo "✓ Python found: $(python --version)"
echo "✓ Node.js found: $(npm --version)"

# Create virtual environment for backend if it doesn't exist
if [ ! -d "backend/venv" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python -m venv backend/venv
fi

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    source backend/venv/Scripts/activate
else
    source backend/venv/bin/activate
fi

# Install backend dependencies
echo "Installing backend dependencies..."
pip install -r backend/requirements.txt -q

# Set Groq API key (user needs to export this)
if [ -z "$GROQ_API_KEY" ]; then
    echo ""
    echo "⚠ Warning: GROQ_API_KEY not set. Please run:"
    echo "  export GROQ_API_KEY=your_key_here"
fi

# Start backend in background
echo ""
echo "Starting FastAPI backend on http://localhost:8000..."
cd backend
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install -q
cd ..

# Start frontend
echo "Starting React frontend on http://localhost:5173..."
cd frontend
npm run dev
