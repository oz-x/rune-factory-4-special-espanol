@echo off
rem Genera dist\RF4S-Espanol-Instalador.exe (requiere: pip install pyinstaller)
cd /d "%~dp0"
python -m PyInstaller --noconfirm --onefile --windowed --name RF4S-Espanol-Instalador ^
  --paths "%~dp0tools" --add-data "%~dp0mod\texto;mod\texto" ^
  --distpath dist --workpath build --specpath build instalador.py
