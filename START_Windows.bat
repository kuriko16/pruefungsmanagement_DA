@echo off
REM Doppelklick startet die Weboberflaeche (braucht Python 3.10+ von python.org)
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 start.py %*
) else (
  python start.py %*
)
if errorlevel 1 (
  echo.
  echo Etwas ist schiefgelaufen. Ist Python installiert? https://www.python.org/downloads/ ^(Haken bei "Add python.exe to PATH" setzen^)
)
pause
