@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1 && set PY=py -3 || set PY=python
echo Final_Eye v1.0 — starting on http://127.0.0.1:9479/
%PY% gui\app.py
pause