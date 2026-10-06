```bat
@echo off
setlocal EnableExtensions

echo ========================================
echo MTG Card Inventory
echo ========================================
echo.
echo Select startup mode:
echo.
echo [1] Python source
echo [2] Compiled EXEs
echo [3] Exit
echo.

set /p MODE="Selection: "

if "%MODE%"=="1" goto PYTHON_MODE
if "%MODE%"=="2" goto EXE_MODE
if "%MODE%"=="3" goto EXIT

echo.
echo Invalid selection.
echo.
pause
exit /b 1


:PYTHON_MODE

echo.
echo ========================================
echo Python Source Mode
echo ========================================
echo.

where python >nul 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python was not found.
    echo.
    echo Make sure Python is installed and available
    echo through the system PATH.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0update_mtgjson.py" (
    echo ERROR: update_mtgjson.py was not found.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0price_server.py" (
    echo ERROR: price_server.py was not found.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0mtgjson_monitor.py" (
    echo ERROR: mtgjson_monitor.py was not found.
    echo.
    pause
    exit /b 1
)

echo All Python components found.
echo.

goto INITIAL_DATABASE_CHECK_PYTHON


:EXE_MODE

echo.
echo ========================================
echo Compiled EXE Mode
echo ========================================
echo.

if not exist "%~dp0MTGJSONUpdater.exe" (
    echo ERROR: MTGJSONUpdater.exe was not found.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0PriceServer.exe" (
    echo ERROR: PriceServer.exe was not found.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0MTGJSONMonitor.exe" (
    echo ERROR: MTGJSONMonitor.exe was not found.
    echo.
    pause
    exit /b 1
)

echo All compiled components found.
echo.

goto INITIAL_DATABASE_CHECK_EXE


:INITIAL_DATABASE_CHECK_PYTHON

echo ========================================
echo Checking MTGJSON databases...
echo ========================================
echo.

python "%~dp0update_mtgjson.py"

if %ERRORLEVEL% EQU 1 goto DATABASE_ERROR

echo.
echo ========================================
echo MTGJSON check complete.
echo ========================================
echo.

goto START_PRICE_SERVER_PYTHON


:INITIAL_DATABASE_CHECK_EXE

echo ========================================
echo Checking MTGJSON databases...
echo ========================================
echo.

"%~dp0MTGJSONUpdater.exe"

if %ERRORLEVEL% EQU 1 goto DATABASE_ERROR

echo.
echo ========================================
echo MTGJSON check complete.
echo ========================================
echo.

goto START_PRICE_SERVER_EXE


:START_PRICE_SERVER_PYTHON

echo Starting MTG Price Server...
echo.

start "MTG Price Server" python "%~dp0price_server.py"

goto WAIT_FOR_SERVER


:START_PRICE_SERVER_EXE

echo Starting MTG Price Server...
echo.

start "MTG Price Server" "%~dp0PriceServer.exe"

goto WAIT_FOR_SERVER


:WAIT_FOR_SERVER

echo Waiting for price server to become ready...
echo.

set /a SERVER_ATTEMPTS=0

:CHECK_SERVER

powershell -NoProfile -Command ^
    "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/health' -TimeoutSec 2; if ($r.status -eq 'ready') { exit 0 } else { exit 1 } } catch { exit 1 }"

if %ERRORLEVEL% EQU 0 goto SERVER_READY

set /a SERVER_ATTEMPTS+=1

if %SERVER_ATTEMPTS% GEQ 30 goto SERVER_ERROR

timeout /t 2 /nobreak >nul
goto CHECK_SERVER


:SERVER_READY

echo.
echo ========================================
echo Price server is ready.
echo ========================================
echo.

if "%MODE%"=="1" goto START_MONITOR_PYTHON
if "%MODE%"=="2" goto START_MONITOR_EXE

goto SERVER_ERROR


:START_MONITOR_PYTHON

echo Starting MTGJSON Monitor...
echo.

start "MTGJSON Monitor" python "%~dp0mtgjson_monitor.py"

goto START_EXCEL


:START_MONITOR_EXE

echo Starting MTGJSON Monitor...
echo.

start "MTGJSON Monitor" "%~dp0MTGJSONMonitor.exe"

goto START_EXCEL


:START_EXCEL

if not exist "%~dp0Store - Inventory Test v2.xlsm" (
    echo.
    echo WARNING: Excel workbook was not found.
    echo.
    echo The Price Server and MTGJSON Monitor are running,
    echo but the Excel application could not be started.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Starting Card Inventory...
echo ========================================
echo.

start "" "%~dp0Store - Inventory Test v2.xlsm"

echo Card Inventory started.
echo.
echo MTG Price Server is running.
echo MTGJSON Monitor is running.
echo.
echo This startup window can now be closed.
echo.

exit /b 0


:DATABASE_ERROR

echo.
echo ========================================
echo MTGJSON DATABASE ERROR
echo ========================================
echo.
echo One or more required MTGJSON databases
echo are unavailable or could not be updated.
echo.
echo Price Server will NOT be started.
echo MTGJSON Monitor will NOT be started.
echo.
pause
exit /b 1


:SERVER_ERROR

echo.
echo ========================================
echo PRICE SERVER ERROR
echo ========================================
echo.
echo The Price Server did not report ready
echo within the expected startup period.
echo.
echo MTGJSON Monitor and Excel will NOT be started.
echo.
echo Check the Price Server output for details.
echo.
pause
exit /b 1


:EXIT

echo.
echo Startup cancelled.
echo.

exit /b 0
```
