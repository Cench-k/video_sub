@echo off
chcp 65001 >nul
setlocal
title AI 자막 추출기 - 설치 및 실행

set "REPO=https://github.com/Cench-k/video_sub.git"
set "DIRNAME=video_sub"

cd /d "%~dp0"

echo =========================================
echo  AI 자막 추출기 (SenseVoice / WhisperX)
echo  설치 및 실행
echo =========================================
echo.

:: ── 소스 위치 결정 ────────────────────────────────────────────────
:: 이 파일이 저장소 안에 있으면 그대로 사용
if exist "app.py" (
    set "TARGET=%CD%"
    goto :have_source
)
:: 옆에 이미 받아둔 폴더가 있으면 재사용
if exist "%DIRNAME%\app.py" (
    set "TARGET=%CD%\%DIRNAME%"
    goto :have_source
)

:: 없으면 git 으로 내려받기
where git >nul 2>nul
if errorlevel 1 (
    echo [오류] git 이 설치되어 있지 않습니다.
    echo.
    echo   방법 1^) https://git-scm.com/download/win 에서 git 설치 후 이 파일을 다시 실행
    echo   방법 2^) 아래 주소에서 ZIP 으로 받아 압축을 푼 뒤,
    echo           그 폴더 안에 이 파일을 넣고 실행
    echo           https://github.com/Cench-k/video_sub/archive/refs/heads/main.zip
    echo.
    pause
    exit /b 1
)

echo [1/4] 소스를 내려받는 중입니다...
git clone "%REPO%" "%DIRNAME%"
if errorlevel 1 (
    echo.
    echo [오류] 소스 내려받기에 실패했습니다. 네트워크 상태를 확인하세요.
    pause
    exit /b 1
)
set "TARGET=%CD%\%DIRNAME%"

:have_source
cd /d "%TARGET%"
echo   - 작업 폴더: %TARGET%
echo.

:: ── python 확인 ──────────────────────────────────────────────────
where python >nul 2>nul
if errorlevel 1 (
    echo [오류] python 을 찾을 수 없습니다.
    echo.
    echo   https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치하세요.
    echo   설치 화면 첫 페이지의 "Add python.exe to PATH" 를 반드시 체크해야 합니다.
    echo.
    pause
    exit /b 1
)

:: ── 가상환경 ─────────────────────────────────────────────────────
echo [2/4] 가상환경(venv)을 확인합니다...
if not exist "venv\Scripts\python.exe" (
    echo   - venv 가 없어 새로 만듭니다...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
)

:: ── 패키지 설치 ──────────────────────────────────────────────────
echo [3/4] 필요한 패키지를 확인합니다...
if not exist "venv\.installed" (
    echo   - 최초 1회 설치를 진행합니다. 수 분 정도 걸릴 수 있습니다...
    ".\venv\Scripts\python.exe" -m pip install --upgrade pip
    ".\venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [오류] 패키지 설치에 실패했습니다.
        echo   네트워크를 확인한 뒤 이 파일을 다시 실행해 주세요.
        pause
        exit /b 1
    )
    echo installed> "venv\.installed"
) else (
    echo   - 이미 설치되어 있습니다. ^(다시 설치하려면 venv\.installed 파일을 지우세요^)
)

:: ── 실행 ─────────────────────────────────────────────────────────
echo.
echo [4/4] 서버를 시작합니다. 잠시 후 브라우저가 열립니다.
echo   * 이 검은 창이 서버 본체입니다. 작업 중에는 닫지 마세요.
echo   * 최초 실행 시 AI 모델 다운로드(수백 MB)로 시간이 걸릴 수 있습니다.
echo.
".\venv\Scripts\python.exe" app.py

echo.
echo 서버가 종료되었습니다.
pause
