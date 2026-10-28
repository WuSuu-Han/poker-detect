@echo off
setlocal
if not exist "%~dp0.venv\pyvenv.cfg" (
  echo Missing .venv\pyvenv.cfg
  exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0.venv\pyvenv.cfg") do if "%%A"=="home " for /f "tokens=*" %%H in ("%%B") do set "BASEPY=%%H\python.exe"
if not defined BASEPY (
  echo Missing home in .venv\pyvenv.cfg
  exit /b 1
)
set "PYTHONPATH=%~dp0.venv\Lib\site-packages"
set "PYTHONIOENCODING=utf-8"
"%BASEPY%" -B %*
exit /b %errorlevel%
