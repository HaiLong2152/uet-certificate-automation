@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

cd /d %~dp0
set PY=python
where py >nul 2>nul && set PY=py
%PY% src\start.py 24020001 "Nguyen Van An" "Ho so hoc bong"
%PY% src\start.py 24020001 "Nguyen Van An" "Ho so hoc bong" ban-cung
%PY% src\start.py 24020002 "Tran Thi Binh" "Khac (can can bo xem xet)"
%PY% src\start.py 23020003 "Le Minh Chau" "Vay von"
pause
