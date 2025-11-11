@echo off
chcp 65001 >nul 2>&1
title Update Old Frontend with Screen Share

echo.
echo ================================
echo  Updating Old Frontend (/ui)
echo ================================
echo.

:: Check if we're in correct directory
if not exist "package.json" (
    echo ERROR: Please run in OpenAvatarChat-WebUI directory
    pause
    exit /b 1
)

:: Build the project
echo [1/3] Building frontend...
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

:: Copy to old frontend location
echo [2/3] Updating old frontend location...
if not exist "..\src\handlers\client\rtc_client\frontend\dist" mkdir "..\src\handlers\client\rtc_client\frontend\dist"

echo Copying files to old frontend directory...
xcopy /s /y "dist\*" "..\src\handlers\client\rtc_client\frontend\dist\"

:: Also update the new location
echo [3/3] Updating new frontend location...  
if not exist "..\static\webui" mkdir "..\static\webui"
xcopy /s /y "dist\*" "..\static\webui\"

echo.
echo ================================
echo  Update Complete!
echo ================================
echo.
echo Updated locations:
echo 1. Old frontend (/ui/): ..\src\handlers\client\rtc_client\frontend\dist\
echo 2. New frontend (/):    ..\static\webui\
echo.
echo Now both internal and external access will have screen sharing!
echo - Internal: https://127.0.0.1:8282/
echo - External: https://liao.uunat.com:8282/ui/
echo.
pause
