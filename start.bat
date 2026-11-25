@echo off
chcp 65001 >nul
set PYTHONUTF8=1
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto setup_venv
goto check_frontend

:setup_venv
echo [Miseclon] Erstelle Python-Umgebung in .venv ...
python -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 goto fail

:check_frontend
if not exist "frontend\dist\index.html" goto build_frontend
goto launch

:build_frontend
echo [Miseclon] Baue Web-Frontend ...
pushd frontend
call npm install
if errorlevel 1 goto fail
call npm run build
if errorlevel 1 goto fail
popd

:launch
.venv\Scripts\python.exe -m backend.run_local
if errorlevel 1 goto fail
goto end

:fail
echo.
echo [FEHLER] Miseclon konnte nicht gestartet werden.
pause
exit /b 1

:end
endlocal
