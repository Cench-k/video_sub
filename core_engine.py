import os
import re
import traceback


def _setup_cache():
    """한글 등 비ASCII 홈 경로 환경에서 modelscope 캐시를 ASCII 경로로 우회."""
    home = os.path.expanduser("~")
    if not home.isascii():
        system_drive = os.environ.get("SYSTEMDRIVE", "C:")
        ascii_cache = f"{system_drive}/modelscope_cache"
        os.makedirs(ascii_cache, exist_ok=True)
        os.environ["MODELSCOPE_CACHE"] = ascii_cache
        os.environ["HF_HOME"] = ascii_cache


def _run_sensevoice(audio_path, device):
    """SenseVoice+VAD로 음성 인식. [(start_s, end_s, text), ...] 반환."""
    from funasr import AutoModel

    model = AutoModel(
        model="iic/SenseVoiceSmall",
        vad_model="fsmn-vad",
        trust_remote_code=True,
        device=device,
    )
    res = model.generate(input=audio_path, language="auto", use_itn=True)

    # 디버그: 첫 번째 아이템의 키 목록과 key 값 출력
    if res:
        print("[DEBUG] res[0] keys:", list(res[0].keys()))
        print("[DEBUG] res[0]['key']:", res[0].get("key", "없음"))
        print("[DEBUG] res[0] timestamp 샘플:", str(res[0].get("timestamp", []))[:200])

    segments = []
    for item in res:
        text = item.get("text", "")
        # 메타 태그 제거
        text = re.sub(r"(<\|[a-zA-Z_]+\|>){2,}", " ", text)
        text = re.sub(r"<\|[^|>]*\|>", "", text).strip()
        if not text:
            continue

        start_s, end_s = -1.0, -1.0

        # timestamp 필드에서 추출 (ms 단위)
        timestamps = item.get("timestamp", [])
        if timestamps:
            try:
                start_s = timestamps[0][0] / 1000
                end_s = timestamps[-1][1] / 1000
            except (IndexError, TypeError):
                pass

        # key에서 추출 (형식: "name_startms_endms")
        if start_s < 0:
            parts = item.get("key", "").rsplit("_", 2)
            if len(parts) == 3:
                try:
                    start_s = int(parts[1]) / 1000
                    end_s = int(parts[2]) / 1000
                except ValueError:
                    pass

        segments.append((start_s, end_s, text))

    return segments


def _detect_ocr_lang(audio_segs):
    """음성 세그먼트 텍스트에 한자가 있으면 중국어 리더, 없으면 한국어 리더 선택."""
    combined = " ".join(text for _, _, text in audio_segs)
    if any("一" <= ch <= "鿿" for ch in combined):
        return ["ch_sim", "en"]
    return ["ko", "en"]


def _run_ocr(video_path, device, ocr_langs=None, crop=None):
    """하드자막 OCR. [(timestamp_s, text), ...] 반환.
    crop=(top%, bottom%, left%, right%) 지정 시 해당 영역만 인식.
    미지정 시 전체 프레임 스캔.
    """
    import cv2
    import easyocr
    import torch

    if ocr_langs is None:
        ocr_langs = ["ko", "en"]

    gpu = torch.cuda.is_available()
    reader = easyocr.Reader(ocr_langs, gpu=gpu)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    sample_interval = max(1, int(fps))  # 1초마다 샘플링

    results = []
    prev_text = ""
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            timestamp = frame_idx / fps
            h, w = frame.shape[:2]

            if crop:
                top_pct, bottom_pct, left_pct, right_pct = crop
                y1 = int(h * top_pct / 100)
                y2 = int(h * bottom_pct / 100)
                x1 = int(w * left_pct / 100)
                x2 = int(w * right_pct / 100)
                region = frame[y1:y2, x1:x2]
            else:
                region = frame

            ocr_res = reader.readtext(region, detail=1)
            sorted_res = sorted(
                [r for r in ocr_res if r[2] > 0.5 and len(r[1].strip()) >= 2],
                key=lambda r: r[0][0][1],
            )
            text = " ".join(r[1] for r in sorted_res).strip()

            if text and text != prev_text:
                results.append((timestamp, text))
                prev_text = text
            elif not text:
                prev_text = ""

        frame_idx += 1

    cap.release()
    return results


def _merge_segments(audio_segs, ocr_segs):
    """
    OCR 우선, 음성은 OCR 공백 구간만 보완.
    Returns: [(time_s, source_label, text), ...]
    """
    merged = []

    # OCR이 커버하는 1초 버킷 집합
    ocr_buckets = set()
    for timestamp, _ in ocr_segs:
        ocr_buckets.add(int(timestamp))

    # OCR 세그먼트 전부 추가
    for timestamp, text in ocr_segs:
        merged.append((timestamp, "자막", text))

    # OCR이 없는 구간의 음성만 추가
    for start, end, text in audio_segs:
        if start < 0 or int(start) not in ocr_buckets:
            merged.append((max(0.0, start), "음성", text))

    merged.sort(key=lambda x: x[0])
    return merged


def _format_combined(merged):
    lines = []
    for time_s, source, text in merged:
        if time_s >= 0:
            m, s = divmod(int(time_s), 60)
            lines.append(f"[{m:02d}:{s:02d} / {source}] {text}")
        else:
            lines.append(f"[{source}] {text}")
    return "\n".join(lines)


def process_audio(audio_path, model_type, hf_token="", crop=None):
    if not audio_path:
        return "오디오 파일을 찾을 수 없습니다."

    output_log = f"[시스템] 분석 시작 (선택된 모델: {model_type})\n"
    output_log += f"[시스템] 파일 위치: {audio_path}\n"
    output_log += "-" * 50 + "\n"

    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # ── 음성 + 하드자막 병합 모드 ──────────────────────────────────────
        if model_type == "combined":
            output_log += "1. 음성 인식(SenseVoice)을 시작합니다...\n"
            output_log += f"   - 사용 장치: {device}\n"

            try:
                from funasr import AutoModel
            except ImportError:
                return output_log + "\n[오류] funasr가 설치되어 있지 않습니다.\n'pip install funasr modelscope'를 실행해주세요."

            _setup_cache()
            audio_segs = _run_sensevoice(audio_path, device)
            output_log += f"   - 음성 세그먼트 {len(audio_segs)}개 추출 완료.\n"

            output_log += "2. 하드자막 OCR을 시작합니다...\n"
            try:
                import cv2
                import easyocr
            except ImportError:
                return output_log + "\n[오류] easyocr 또는 opencv-python이 설치되어 있지 않습니다.\n'pip install easyocr opencv-python'을 실행해주세요."

            ocr_langs = _detect_ocr_lang(audio_segs)
            ocr_segs = _run_ocr(audio_path, device, ocr_langs, crop=crop)
            output_log += f"   - OCR 세그먼트 {len(ocr_segs)}개 추출 완료.\n"

            output_log += "3. 결과를 병합합니다...\n\n"
            merged = _merge_segments(audio_segs, ocr_segs)

            if merged:
                output_log += "[✅ 병합 결과]\n"
                output_log += _format_combined(merged)
            else:
                output_log += "결과가 비어 있습니다."
            return output_log

        # ── SenseVoice 단독 ────────────────────────────────────────────────
        elif model_type == "sensevoice":
            output_log += "1. SenseVoice 파이프라인 (FunASR)을 초기화 중입니다...\n"
            output_log += "   (첫 실행 시 모델 다운로드에 시간이 소요될 수 있습니다.)\n"

            try:
                from funasr import AutoModel
            except ImportError:
                return output_log + "\n[오류] funasr 모듈이 설치되어 있지 않습니다.\n'pip install funasr modelscope'를 실행해주세요."

            output_log += f"   - 사용 장치(Device): {device}\n"
            _setup_cache()

            model = AutoModel(
                model="iic/SenseVoiceSmall",
                vad_model="fsmn-vad",
                trust_remote_code=True,
                device=device,
            )
            output_log += "2. 음성 활동 감지(VAD) 장착 완료! 긴 영상도 안전하게 인식을 진행합니다...\n"

            res = model.generate(input=audio_path, language="auto", use_itn=True)

            output_log += "\n[✅ 추출 결과]\n"
            if res and "text" in res[0]:
                raw_text = res[0]["text"]
                raw_text = re.sub(r"<\|speaker_(\d+)\|>", r"\n\n[SPEAKER_\1] ", raw_text)
                formatted = re.sub(r"(<\|[a-zA-Z_]+\|>){2,}", "\n\n", raw_text)
                formatted = re.sub(r"<\|[^|>]*\|>", "", formatted)
                formatted = re.sub(
                    r"\[(zh|en|ja|ko|yue|auto|NEUTRAL|HAPPY|SAD|ANGRY|FEARFUL|DISGUSTED|SURPRISED|EMO_UNKNOWN|Speech|BGM|Applause|Laughter|Cry|withitn|woitn)\]\s*",
                    "",
                    formatted,
                )
                formatted = re.sub(r"([。！？；])\s*", r"\1\n", formatted)
                formatted = re.sub(r"([\?!])\s+", r"\1\n", formatted)
                formatted = re.sub(r"\n{3,}", "\n\n", formatted)
                output_log += formatted.strip()
            else:
                output_log += "결과가 비어 있습니다."
            return output_log

        # ── WhisperX ───────────────────────────────────────────────────────
        elif model_type == "whisperx":
            output_log += "1. WhisperX 파이프라인을 초기화 중입니다...\n"

            try:
                import whisperx
            except ImportError:
                return output_log + "\n[오류] whisperx 모듈이 설치되어 있지 않습니다.\n설치 가이드에 따라 먼저 whisperx를 설치해 주세요."

            output_log += f"   - 사용 장치(Device): {device}\n"

            model = whisperx.load_model("large-v3", device, compute_type="float16" if device == "cuda" else "int8")
            audio = whisperx.load_audio(audio_path)
            result = model.transcribe(audio, batch_size=8)
            output_log += "   - 오디오 텍스트화 완료.\n"

            if hf_token:
                output_log += "2. 화자 분리(Diarization)를 시작합니다...\n"
                try:
                    diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
                    diarize_segments = diarize_model(audio)
                    result = whisperx.assign_word_speakers(diarize_segments, result)
                    output_log += "   - 화자 분리 완료.\n\n"
                except Exception as e:
                    output_log += f"\n[경고] 화자 분리 중 오류 발생: {str(e)}\n\n"
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

    except Exception:
        output_log += f"\n[심각한 오류 발생]\n{traceback.format_exc()}"
        return output_log
