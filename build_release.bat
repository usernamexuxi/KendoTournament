@echo off
rem 다른 PC 에 줄 실행 파일 하나를 만든다: dist\KendoTournament.exe (폴더·압축 없이 이 파일만 넘긴다)
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pytest -q || goto :failed
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --windowed --name KendoTournament --paths src --add-data "src\kendo_tournament\assets;kendo_tournament\assets" src\kendo_tournament\main.py || goto :failed
echo.
echo 완료: dist\KendoTournament.exe  (이 파일 하나만 넘기면 됩니다)
exit /b 0
:failed
echo.
echo 실패했습니다. 위 메시지를 확인해 주세요.
exit /b 1
