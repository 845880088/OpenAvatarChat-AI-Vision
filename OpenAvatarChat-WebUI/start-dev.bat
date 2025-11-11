@echo off
chcp 65001 >nul 2>&1
title OpenAvatarChat-WebUI Development Server

echo.
echo ================================
echo  OpenAvatarChat-WebUI Frontend
echo ================================
echo.

:: Check if in correct directory
if not exist "package.json" (
    echo ERROR: Please run this script in OpenAvatarChat-WebUI directory
    echo Current directory: %CD%
    echo.
    pause
    exit /b 1
)

:: Check if main project exists
if not exist "..\src\demo.py" (
    echo ERROR: Main project not found in parent directory
    echo Please ensure this is inside OpenAvatarChat-250916 project
    echo.
    pause
    exit /b 1
)

echo [1/4] Environment check - OK

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found
    echo Please install Node.js from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

echo [2/4] Node.js check - OK

:: Check package manager and install dependencies
pnpm --version >nul 2>&1
if errorlevel 1 (
    echo [3/4] Package manager - npm
    echo Installing dependencies with npm...
    call npm install
    if errorlevel 1 (
        echo ERROR: npm install failed
        pause
        exit /b 1
    )
    set "PKG_MGR=npm"
) else (
    echo [3/4] Package manager - pnpm  
    echo Installing dependencies with pnpm...
    call pnpm install
    if errorlevel 1 (
        echo ERROR: pnpm install failed
        pause
        exit /b 1
    )
    set "PKG_MGR=pnpm"
)

echo Dependencies installed successfully

:: Start development server
echo.
echo [4/4] Starting development server...
echo.
echo ================================
echo   Frontend Server Starting
echo ================================
echo Frontend URL: http://localhost:5173
echo Backend Proxy: https://127.0.0.1:8282
echo.
echo WARNING: Ensure backend is running first!
echo Backend startup: Double-click 04运行程序-lam-VL.bat in main directory
echo.
echo Screen Sharing feature integrated - use top-right control panel
echo.

:: Start server based on package manager
if "%PKG_MGR%"=="pnpm" (
    echo Starting with pnpm dev...
    pnpm dev
) else (
    echo Starting with npm run dev...  
    npm run dev
)

:: Server stopped
echo.
echo ================================
echo Development server stopped
echo ================================
pause
