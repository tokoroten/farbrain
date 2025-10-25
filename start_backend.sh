#!/bin/bash

# Start backend server
echo "Starting FarBrain backend..."

cd backend

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed!"
    echo "Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "Installing dependencies..."
    uv sync
fi

# Start the server
echo "Starting FastAPI server on http://localhost:8000"
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
