@echo off

echo ========================================
echo MTG Card Inventory
echo ========================================
echo.

echo Checking MTGJSON databases...
echo.

"%~dp0MTGJSONUpdater.exe"

if %ERRORLEVEL% EQU 1 (
    echo.
    echo ========================================
    echo MTGJSON DATABASE ERROR
    echo ========================================
    echo.
    echo One or more required MTGJSON databases
    echo are unavailable.
    echo.
    echo Price server will NOT be started.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo MTGJSON check complete.
echo ========================================
echo.

echo Starting MTG Price Server...
echo.

start "" "%~dp0PriceServer.exe"

echo Waiting for price server to become ready...
echo.

:CHECK_SERVER

powershell -NoProfile -Command ^
    "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/health' -TimeoutSec 2; if ($r.status -eq 'ready') { exit 0 } else { exit 1 } } catch { exit 1 }"

if %ERRORLEVEL% EQU 0 goto SERVER_READY

timeout /t 2 /nobreak >nul
goto CHECK_SERVER

:SERVER_READY

echo.
echo ========================================
echo Price server is ready.
echo ========================================
echo.
echo Starting Card Inventory...
echo.

start "" "%~dp0Store - Inventory Test v2.xlsm"

exit
