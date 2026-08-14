# 🎙️ 로컬 자막 추출기 (SenseVoice / WhisperX)

영상·오디오 파일을 로컬 PC에서 AI로 자막 추출하는 Gradio 웹 UI입니다.
외부 API 호출 없이 모두 로컬에서 동작합니다.

## 기능
- **SenseVoice (FunASR)** — 중국어 포함 다국어 자동 인식, 감정/이벤트 태그, VAD로 긴 영상 안정 처리
- **WhisperX** — 고정밀 인식 + **화자 분리**(pyannote, HuggingFace 토큰 필요)
- 드래그 앤 드롭으로 파일 업로드 즉시 분석 시작

## 요구 사양
- Python 3.10+
- GPU 권장 (CUDA 지원 NVIDIA). CPU로도 동작하지만 매우 느림
- 최초 실행 시 AI 모델 자동 다운로드 (수백 MB)

## 설치

### 방법 1. 원클릭 (Windows 권장)

**[⬇ 설치_및_실행.bat 다운로드](https://github.com/Cench-k/video_sub/raw/main/%EC%84%A4%EC%B9%98_%EB%B0%8F_%EC%8B%A4%ED%96%89.bat)**

받은 파일을 원하는 폴더에 두고 더블클릭하면 소스 내려받기 → 가상환경 생성 → 패키지 설치 → 실행까지 한 번에 진행됩니다.
두 번째 실행부터는 설치를 건너뛰고 바로 서버가 뜹니다.

- 미리 준비할 것: [Python 3.10+](https://www.python.org/downloads/) (설치 시 **"Add python.exe to PATH"** 체크), [Git for Windows](https://git-scm.com/download/win)
- git 없이 쓰려면 [ZIP으로 받아](https://github.com/Cench-k/video_sub/archive/refs/heads/main.zip) 압축을 푼 폴더 안에 이 bat 파일을 넣고 실행하세요.
- 브라우저가 bat 다운로드를 차단하면 "유지" 또는 "계속"을 선택하세요.
- 패키지를 다시 설치하고 싶으면 `venv\.installed` 파일을 지우고 실행하면 됩니다.

### 방법 2. 수동

```bash
git clone https://github.com/Cench-k/video_sub.git
cd video_sub

python -m venv venv
venv\Scripts\activate          # (Linux/Mac: source venv/bin/activate)

pip install -r requirements.txt
```

### WhisperX 를 사용할 경우 추가 설치
```bash
pip install whisperx
```
※ `torch` CUDA 빌드가 필요하면 https://pytorch.org/get-started/locally/ 에서 환경에 맞는 명령으로 설치하세요.

## 실행
Windows: `설치_및_실행.bat` 또는 `자막추출기_실행.bat` 더블클릭
(`자막추출기_실행.bat` 은 설치가 이미 끝난 폴더에서 서버만 띄웁니다)

또는 수동:
```bash
venv\Scripts\activate
python app.py
```

브라우저에서 http://127.0.0.1:7860 접속.

> **주의:** 검은 콘솔창이 Gradio 서버 본체입니다. 작업 중에 닫지 마세요. 닫으면 브라우저에서 `ERR_CONNECTION_REFUSED` 가 납니다.

## 화자 분리 (WhisperX) 사용법
1. https://huggingface.co/settings/tokens 에서 **Read 권한 토큰** 발급
2. 아래 두 모델의 "Agree and access repository" 클릭
   - https://huggingface.co/pyannote/segmentation-3.0
   - https://huggingface.co/pyannote/speaker-diarization-3.1
3. 웹 UI에서 모델을 `whisperx` 로 선택 → 토큰 입력 → 파일 업로드

## 라이선스
- 본 저장소: MIT
- 사용된 오픈소스 모델/라이브러리 라이선스를 각 배포처에서 확인하세요
  - FunASR / SenseVoice: MIT
  - WhisperX: BSD-4
  - pyannote.audio: MIT (모델 가중치는 HF 약관 별도)
  - Gradio: Apache-2.0

## 주의사항
- 추출 결과는 참고용입니다. 전문 자막 제작 시 수동 검수 권장.
- 업로드한 미디어 파일은 로컬에만 저장되며 외부로 전송되지 않습니다.
