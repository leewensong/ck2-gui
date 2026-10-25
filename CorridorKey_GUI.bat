@echo off
cd /d "%~dp0"
if exist "%~dp0runtime\pythonw.exe" (
    start "" "%~dp0runtime\pythonw.exe" -I -B "%~dp0bootstrap.py" %*
    exit /b 0
)
if not exist "%~dp0..\venv\Scripts\pythonw.exe" (
    echo Missing Python environment.
    echo Create the CorridorKey 2.0 venv in the parent folder first, then install:
    echo     ..\venv\Scripts\python.exe -m pip install -r requirements-gui.txt
    pause
    exit /b 1
)
start "" "%~dp0..\venv\Scripts\pythonw.exe" -m ck2gui %*
