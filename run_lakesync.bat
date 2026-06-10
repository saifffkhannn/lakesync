@echo off
setlocal
cd /d "%~dp0"

echo ====================================================
echo    LakeSync Platform - Development Server Starter
echo ====================================================

:: 1. Start the Ingestion Engine Backend on port 8001
echo [1/5] Starting Ingestion Engine Backend (Port 8001) in separate window...
cd ingestion_engine
start "LakeSync Ingestion Backend" cmd /c "uvicorn api:app --port 8001"
cd ..

:: 2. Start the ABAP Conversion Backend on port 5000
echo [2/5] Starting ABAP Conversion Backend (Port 5000) in separate window...
cd Conversion_ABAP\backend
start "LakeSync ABAP Backend" cmd /c "python flask_app.py"
cd ..\..

:: 3. Start the API Gateway on port 8000
echo [3/5] Starting API Gateway (Port 8000) in separate window...
start "LakeSync API Gateway" cmd /c "python api_gateway.py"

:: 4. Start the Frontend (Vite)
echo [4/5] Starting LakeSync Frontend UI in separate window...
cd lakesync
start "LakeSync Frontend UI" cmd /c "npm run dev"
cd ..

:: 5. Give them a few seconds to boot up then open the link
echo [5/5] Waiting for servers to initialize...
timeout /t 6 /nobreak > nul

echo.
echo Opening LakeSync at http://localhost:5173
start "" "http://localhost:5173"

echo.
echo ----------------------------------------------------
echo Success: All LakeSync services are running.
echo To stop services, close the separate terminal windows.
echo ----------------------------------------------------
echo.
pause
