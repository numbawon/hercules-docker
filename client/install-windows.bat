@echo off
rem Double-click to install the Family RO client (see install-windows.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1" %*
pause
