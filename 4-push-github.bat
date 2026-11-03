@echo off
chcp 65001 >nul
cd /d %~dp0
git add -A
git commit -m "Add to-be BPMN (task 5): auto-approval, PDF with QR, e-copy by email"
git remote set-url origin https://github.com/dungvuColder/uet-certificate-automation.git
git push -u origin main
pause
