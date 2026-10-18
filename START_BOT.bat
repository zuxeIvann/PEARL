@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run INSTALL_FIRST.bat first. & pause & exit /b 1)
if not exist ".env" (echo Missing .env. Run INSTALL_FIRST.bat first. & pause & exit /b 1)
:restart
echo [%date% %time%] Starting PEARL OF HEAVEN Aegis Guard...
".venv\Scripts\python.exe" -u bot.py
set "code=%errorlevel%"
echo Bot exited with code %code%. Restarting in 20 seconds. Close this window to stop.
timeout /t 20 /nobreak >nul
goto restart
