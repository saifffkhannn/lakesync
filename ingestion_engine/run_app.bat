@echo off
setlocal
cd /d "%~dp0"

echo ====================================================
echo    Ingestion Engine - Development Server Starter
echo ====================================================

:: 1. Start the Backend (FastAPI)
echo [1/3] Starting Backend API in separate window...
start "Data Ingestion API" cmd /c "uvicorn api:app"

:: 2. Start the Frontend (Vite)
echo [2/3] Starting Frontend UI in separate window...
cd incremental-ui
start "Data Ingestion UI" cmd /c "npm run dev"

:: 3. Give them a few seconds to boot up then open the link
echo [3/3] Waiting for servers to initialize...
timeout /t 6 /nobreak > nul

echo.
echo Opening Ingestion Engine at http://localhost:5173
start "" "http://localhost:5173"

echo.
echo ----------------------------------------------------
echo Success: Services are running.
echo To stop services, close the separate terminal windows.
echo ----------------------------------------------------
echo.
pause
