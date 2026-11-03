@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d %~dp0
set PY=python
where py >nul 2>nul && set PY=py
%PY% src\worker.py
pause
