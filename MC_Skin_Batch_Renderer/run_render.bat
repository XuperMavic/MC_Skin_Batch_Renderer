@echo off
cd "%~dp0"

REM Install dependencies silently
python -m pip install pillow >nul 2>&1

REM Run the application directly
python MCskin_renderer.py

REM Exit silently (this line will only execute if the application exits)
exit
