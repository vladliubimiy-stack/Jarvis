@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" jarvis_voice.py
) else (
  python jarvis_voice.py
)
endlocal
