@echo off
cd /d "%~dp0"
echo CCF static website: http://localhost:8088
echo Press Ctrl+C to stop.
python -m http.server 8088 --directory docs
pause
