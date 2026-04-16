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

```bash
git clone https://github.com/<사용자명>/<저장소명>.git
cd <저장소명>

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
Windows: `자막추출기_실행.bat` 더블클릭

또는 수동:
```bash
venv\Scripts\activate
python app.py
```

브라우저에서 http://127.0.0.1:7861 접속.

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
