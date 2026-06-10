@echo off
title Data Migration Starter

if /I "%~1"=="backend" goto start_backend
if /I "%~1"=="frontend" goto start_frontend

echo Starting the Data Migration App...

:: 1. Start the Python Backend
echo Starting Backend...
start "Backend" cmd /k call "%~f0" backend

:: 2. Start the Frontend
echo Starting Frontend...
start "Frontend" cmd /k call "%~f0" frontend

echo Both services are starting! You can minimize these terminal windows.
exit /b 0

:start_backend
cd /d "%~dp0BACKEND" || exit /b 1

if not exist ".venv\Scripts\python.exe" (
    echo Creating backend virtual environment...
    py -3 -m venv .venv || python -m venv .venv || exit /b 1
)

call ".venv\Scripts\activate.bat" || exit /b 1

if not exist ".venv\.deps_installed" (
    echo Installing backend dependencies...
    python -m pip install --upgrade pip || exit /b 1
    python -m pip install -r requirements.txt || exit /b 1
    type nul > ".venv\.deps_installed"
) else (
    echo Backend environment found. Skipping dependency install.
)

echo Starting backend API...
python api.py
exit /b %ERRORLEVEL%

:start_frontend
cd /d "%~dp0Frontend" || exit /b 1

if not exist node_modules (
    echo node_modules not found. Installing dependencies...
    call npm install || exit /b 1
) else (
    echo node_modules found. Skipping install.
)

echo Starting frontend...
call npm start
exit /b %ERRORLEVEL%
