@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (echo Python launcher not found. Install Python 3.11 or 3.12 from python.org & pause & exit /b 1)
py -3 -m venv .venv
if errorlevel 1 (echo Failed to create venv & pause & exit /b 1)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (echo Package installation failed & pause & exit /b 1)
if not exist .env copy .env.example .env >nul
echo Installation complete. Edit .env to set DISCORD_TOKEN and GUILD_ID.
pause
