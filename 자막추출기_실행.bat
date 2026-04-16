@echo off
title AI 자막 추출기 (SenseVoice / WhisperX)

echo =========================================
echo  로컬 자막 추출기를 시작합니다...
echo  AI 모델을 준비하는 중입니다 (최초 실행 시 다운로드 시간이 걸립니다)
echo =========================================

:: 배치 파일이 있는 폴더로 이동 (절대경로 의존 제거)
cd /d %~dp0

:: 가상환경이 없으면 안내
if not exist ".\venv\Scripts\python.exe" (
    echo [오류] venv 가상환경이 없습니다.
    echo 아래 명령으로 먼저 환경을 만드세요:
    echo     python -m venv venv
    echo     venv\Scripts\activate
    echo     pip install -r requirements.txt
    pause
    exit /b 1
)

:: 가상환경 파이썬으로 서버 구동
.\venv\Scripts\python.exe app.py

pause
