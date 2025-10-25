@echo off
REM Start frontend server (Windows)

echo Starting FarBrain frontend...

cd frontend

REM Check if .env exists
if not exist .env (
    echo Warning: .env file not found, creating from .env.example
    copy .env.example .env
)

REM Check if node_modules exists
if not exist node_modules (
    echo Installing dependencies...
    npm install
)

REM Start the development server
echo Starting Vite dev server on http://localhost:5173
npm run dev
