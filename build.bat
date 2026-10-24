@echo off
rem Gera Backup.exe na pasta do projeto
if not exist .venv py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -q -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests || exit /b 1
.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name Backup app.py || exit /b 1
copy /Y dist\Backup.exe Backup.exe >nul
echo Pronto: Backup.exe
