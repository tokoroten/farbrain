#!/bin/bash

# Start frontend server
echo "Starting FarBrain frontend..."

cd frontend

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found, creating from .env.example"
    cp .env.example .env
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the development server
echo "Starting Vite dev server on http://localhost:5173"
npm run dev
