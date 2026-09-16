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

### WhisperX 를 사용할 경우: 전용 venv 가 필요합니다

whisperx 는 `huggingface-hub<1.0` 을, gradio 6 은 `>=1.16` 을 요구해서 **한 환경에 함께 설치할 수 없습니다.**
그래서 whisperx 만 별도 venv 에 두고, `core_engine` 이 `whisperx_worker.py` 를 서브프로세스로 호출합니다.

```bash
python -m venv venv_whisperx
venv_whisperx\Scripts\python.exe -m pip install whisperx
```

GPU 를 쓰려면 그 venv 에도 CUDA 빌드를 넣어야 합니다. whisperx 는 `torch~=2.8.0` 을 요구합니다.
같은 버전 번호의 CPU 휠이 이미 깔려 있으면 pip 가 건너뛰므로 `--force-reinstall` 이 필요합니다.

```bash
venv_whisperx\Scripts\python.exe -m pip install --force-reinstall --no-deps ^
  torch==2.8.0 torchaudio==2.8.0 torchvision==0.23.0 ^
  --index-url https://download.pytorch.org/whl/cu126
```

동작 확인:
```bash
venv_whisperx\Scripts\python.exe -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_arch_list())"
```

### 메인 venv 에 CUDA torch 넣기
`requirements.txt` 의 `torch` 는 PyPI 기본(CPU) 휠입니다. GPU 를 쓰려면 카드에 맞는 빌드를 직접 넣으세요.
GTX 1060 등 Pascal(sm_61) 카드는 cu124 계열이 안전합니다 (최신 cu128 빌드는 Pascal 커널이 빠져 있습니다).

```bash
venv\Scripts\python.exe -m pip install torch==2.6.0 torchaudio==2.6.0 torchvision==0.21.0 ^
  --index-url https://download.pytorch.org/whl/cu124
```

`torch` 는 자동 업데이트 대상이 아니므로 한 번 맞춰두면 유지됩니다.

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

## 자동 업데이트
bat 파일로 실행하면 서버가 뜨기 전에 `updater.py` 가 두 가지를 확인합니다.

**1) 프로그램 버전** — 매 실행마다 저장소를 확인해 새 버전이 있으면 자동으로 내려받습니다.
- 소스를 직접 고친 상태(추적 중인 파일이 수정됨)면 그 내용을 지키기 위해 업데이트를 건너뜁니다.
- `requirements.txt` 가 바뀐 경우에만 패키지를 다시 설치합니다. (`venv\.reqhash` 로 판별)
- bat 파일 자체가 갱신되면 "다시 실행해 주세요" 안내 후 종료합니다. 한 번 더 실행하면 새 버전으로 동작합니다.

**2) 엔진 버전** — `funasr`, `modelscope`, `easyocr`, `gradio`, `whisperx` 를 PyPI 최신 버전으로 유지합니다.
- 조회는 하루에 한 번만 합니다. (`venv\.enginecheck`)
- **`torch` / `torchaudio` 는 확인만 하고 자동 업그레이드하지 않습니다.** 자동 업그레이드하면 CUDA 빌드가 CPU 전용 휠로 조용히 바뀔 수 있어서입니다. 새 버전 안내가 떠도 직접 판단해 설치하세요.
- `whisperx` 는 `venv_whisperx` 쪽에서 따로 확인·갱신합니다. 전용 venv 가 없으면 안내만 표시합니다.
- 인터넷이 안 되면 조용히 건너뛰고 현재 버전으로 실행합니다.

환경 변수로 동작을 바꿀 수 있습니다.
```bat
set SUBEXT_CHECK_ONLY=1           :: 버전만 확인하고 갱신하지 않음
set SUBEXT_FORCE_ENGINE_CHECK=1   :: 하루 한 번 제한을 무시하고 즉시 조회
```

> AI 모델 가중치(SenseVoice, VAD)는 자동 갱신 대상이 **아닙니다**. ModelScope 허브 API가 WAF 에 막혀 403 이 나는 문제 때문에 로컬 캐시를 그대로 쓰도록 고정돼 있습니다.

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
