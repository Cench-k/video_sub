import os
import traceback

def process_audio(audio_path, model_type, hf_token=""):
    """
    전달받은 오디오/영상을 모델에 따라 처리합니다.
    (실제 사용자 PC에 패키지가 깔려있는지 확인하기 위해 try-except로 감싸 안전하게 처리)
    """
    if not audio_path:
        return "오디오 파일을 찾을 수 없습니다."

    output_log = f"[시스템] 분석 시작 (선택된 모델: {model_type})\n"
    output_log += f"[시스템] 파일 위치: {audio_path}\n"
    output_log += "-" * 50 + "\n"

    try:
        if model_type == "sensevoice":
            output_log += "1. SenseVoice 파이프라인 (FunASR)을 초기화 중입니다...\n   (첫 실행 시 모델 다운로드에 시간이 소요될 수 있습니다.)\n"
            
            # 파이썬 패키지가 없는 경우를 대비한 예외 처리
            try:
                from funasr import AutoModel
            except ImportError:
                return output_log + "\n[오류] funasr 모듈이 설치되어 있지 않습니다.\n터미널에서 'pip install funasr modelscope'를 실행해주세요."

            # 모델 로드 (CUDA 자동 탐색)
            # device 판단 (GPU가 없으면 알아서 CPU로 돌아가지만 많이 느려집니다.)
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            output_log += f"   - 사용 장치(Device): {device}\n"

            # sentencepiece가 경로의 한글 등 비ASCII 문자를 처리 못하는 Windows 문제 우회:
            # 홈 경로에 비ASCII가 있을 때만 시스템 드라이브의 ASCII 경로로 캐시를 리디렉션합니다.
            home = os.path.expanduser("~")
            if not home.isascii():
                system_drive = os.environ.get("SYSTEMDRIVE", "C:")
                ascii_cache = f"{system_drive}/modelscope_cache"
                os.makedirs(ascii_cache, exist_ok=True)
                os.environ["MODELSCOPE_CACHE"] = ascii_cache
                os.environ["HF_HOME"] = ascii_cache

            # 긴 영상 처리를 위해 VAD(fsmn-vad) 모델을 함께 불러옵니다.
            # VAD가 알아서 침묵 구간을 가위질하여 SenseVoice의 환각/반복 증상을 방지합니다.
            model = AutoModel(
                model="iic/SenseVoiceSmall", 
                vad_model="fsmn-vad",
                trust_remote_code=True, 
                device=device
            )
            output_log += "2. 음성 활동 감지(VAD) 장착 완료! 긴 영상도 안전하게 인식을 진행합니다...\n"
            
            # SenseVoice 추론
            res = model.generate(
                input=audio_path, 
                language="auto",  # 언어 자동 감지
                use_itn=True      # 기호, 구두점 정리 활성화
            )
            
            output_log += "\n[✅ 추출 결과]\n"
            if len(res) > 0 and 'text' in res[0]:
                import re
                raw_text = res[0]['text']
                # 0) 화자 태그 보존 — 메타 그룹 치환 전에 플레이스홀더로 분리
                raw_text = re.sub(r"<\|speaker_(\d+)\|>", r"\n\n[SPEAKER_\1] ", raw_text)
                # 1) SenseVoice 메타 태그 그룹을 단락 구분자로 치환
                #    예: <|zh|><|NEUTRAL|><|Speech|><|woitn|>  →  \n\n
                #    (감정: NEUTRAL/HAPPY/SAD/ANGRY/FEARFUL/DISGUSTED/SURPRISED/EMO_UNKNOWN)
                #    (이벤트: Speech/BGM/Applause/Laughter/Cry)
                formatted_text = re.sub(
                    r"(<\|[a-zA-Z_]+\|>){2,}",
                    "\n\n",
                    raw_text,
                )
                # 2) 남은 단일 태그 제거 (대괄호 형태 변환된 것 포함)
                formatted_text = re.sub(r"<\|[^|>]*\|>", "", formatted_text)
                formatted_text = re.sub(r"\[(zh|en|ja|ko|yue|auto|NEUTRAL|HAPPY|SAD|ANGRY|FEARFUL|DISGUSTED|SURPRISED|EMO_UNKNOWN|Speech|BGM|Applause|Laughter|Cry|withitn|woitn)\]\s*", "", formatted_text)
                # 3) 문장 부호 뒤에 줄바꿈 (중·영 공통)
                formatted_text = re.sub(r"([。！？；])\s*", r"\1\n", formatted_text)
                formatted_text = re.sub(r"([\?!])\s+", r"\1\n", formatted_text)
                # 4) 연속 개행 정리
                formatted_text = re.sub(r"\n{3,}", "\n\n", formatted_text)
                output_log += formatted_text.strip()
            else:
                output_log += "결과가 비어 있습니다."
                
            return output_log

        elif model_type == "whisperx":
            output_log += "1. WhisperX 파이프라인을 초기화 중입니다...\n"
            
            try:
                import whisperx
            except ImportError:
                return output_log + "\n[오류] whisperx 모듈이 설치되어 있지 않습니다.\n설치 가이드에 따라 먼저 whisperx를 설치해 주세요."

            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            output_log += f"   - 사용 장치(Device): {device}\n"

            # 1단계: WhisperX 로드 및 텍스트 추출
            model = whisperx.load_model("large-v3", device, compute_type="float16" if device=="cuda" else "int8")
            audio = whisperx.load_audio(audio_path)
            result = model.transcribe(audio, batch_size=8)
            output_log += "   - 오디오 텍스트화 완료.\n"

            # 2단계: 화자 분리 (Diarization)
            if hf_token:
                output_log += "2. 화자 분리(Diarization)를 시작합니다...\n"
                try:
                    diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
                    diarize_segments = diarize_model(audio)
                    # 화자 결과 매핑
                    result = whisperx.assign_word_speakers(diarize_segments, result)
                    output_log += "   - 화자 분리 완료.\n\n"
                except Exception as e:
                    output_log += f"\n[경고] 화자 분리 중 오류 발생 (토큰 문제일 수 있습니다): {str(e)}\n\n"
            else:
                output_log += "   - HuggingFace 토큰이 없어 화자 분리는 생략합니다.\n\n"

            output_log += "[✅ 추출 결과]\n"
            for segment in result["segments"]:
                speaker = segment.get("speaker", "SPEAKER_UNKNOWN")
                start = round(segment.get("start", 0), 2)
                end = round(segment.get("end", 0), 2)
                text = segment.get("text", "")
                output_log += f"[{speaker}] ( {start}s ~ {end}s ) : {text}\n"
                
            return output_log

    except Exception as e:
        output_log += f"\n[심각한 오류 발생]\n{traceback.format_exc()}"
        return output_log
