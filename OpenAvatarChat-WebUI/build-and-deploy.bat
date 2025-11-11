@echo off
chcp 65001 >nul 2>&1
title Build and Deploy WebUI

echo.
echo ================================
echo  Building WebUI for Production
echo ================================
echo.

:: Check environment
if not exist "package.json" (
    echo ERROR: Please run in OpenAvatarChat-WebUI directory
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "node_modules" (
    echo [1/3] Installing dependencies...
    pnpm --version >nul 2>&1
    if errorlevel 1 (
        call npm install
    ) else (
        call pnpm install
    )
) else (
    echo [1/3] Dependencies already installed
)

:: Build for production
echo [2/3] Building for production...
pnpm --version >nul 2>&1
if errorlevel 1 (
    call npm run build
) else (
    call pnpm build
)

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

:: Deploy to backend static directory
echo [3/3] Deploying to backend...

:: Create static directory in backend
if not exist "..\static" mkdir "..\static"
if not exist "..\static\webui" mkdir "..\static\webui"

:: Copy built files
echo Copying files to backend static directory...
xcopy /s /y "dist\*" "..\static\webui\"

echo.
echo ================================
echo  Build and Deploy Complete!
echo ================================
echo.
echo Frontend files deployed to: ..\static\webui\
echo.
echo Now configure backend to serve static files:
echo 1. Start backend: 04运行程序-lam-VL.bat
echo 2. Access via: https://liao.uunat.com:8282/webui/
echo.
pause
