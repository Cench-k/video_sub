@echo off
chcp 65001 >nul
title AI 자막 추출기 (SenseVoice / WhisperX)

:: 업데이트로 이 bat 파일이 교체되어도 실행이 깨지지 않도록
:: 임시 폴더의 사본에서 다시 실행한다.
if defined SUBEXT_HOME goto :run
set "SUBEXT_HOME=%~dp0"
copy /y "%~f0" "%TEMP%\subext_launcher.bat" >nul
if errorlevel 1 goto :run
"%TEMP%\subext_launcher.bat"
exit /b %errorlevel%

:run
cd /d "%SUBEXT_HOME%"

echo =========================================
echo  로컬 자막 추출기
echo =========================================
echo.

:: 가상환경이 없으면 안내
if not exist ".\venv\Scripts\python.exe" goto :novenv

:: 버전 확인 및 자동 업데이트
if not exist "updater.py" goto :skip_update
.\venv\Scripts\python.exe updater.py
if errorlevel 10 goto :launcher_updated
echo.

:skip_update
echo [실행] 서버를 시작합니다. 잠시 후 브라우저에서 열어 주세요.
echo   * 이 검은 창이 서버 본체입니다. 작업 중에는 닫지 마세요.
echo   * 최초 실행 시 AI 모델 다운로드로 시간이 걸릴 수 있습니다.
echo.
.\venv\Scripts\python.exe app.py
echo.
echo 서버가 종료되었습니다.
pause
exit /b 0

:launcher_updated
echo.
echo   업데이트를 적용하려면 이 창을 닫고 바로 가기를 다시 실행해 주세요.
echo.
pause
exit /b 0

:novenv
echo [오류] venv 가상환경이 없습니다.
echo 아래 명령으로 먼저 환경을 만드세요:
echo     python -m venv venv
echo     venv\Scripts\activate
echo     pip install -r requirements.txt
echo.
echo 또는 설치_및_실행.bat 을 실행하세요.
pause
exit /b 1
