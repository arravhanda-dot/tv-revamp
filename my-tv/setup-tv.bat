@echo off
rem Double-click to set up the TV. Needs Python from python.org (tick "Add python.exe to PATH").
cd /d "%~dp0.."
py my-tv\setup_tv.py %*
if errorlevel 9009 python my-tv\setup_tv.py %*
pause
