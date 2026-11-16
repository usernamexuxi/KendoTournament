@echo off
rem 개발 중 확인용 실행. 배포본은 build_release.bat 으로 만든다.
cd /d "%~dp0"
".venv\Scripts\pythonw.exe" -m kendo_tournament.main
