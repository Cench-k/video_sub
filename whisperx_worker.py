"""venv_whisperx 안에서 실행되는 WhisperX 작업자.

whisperx 는 huggingface-hub<1.0 을 요구하고 gradio 6 은 >=1.16 을 요구해
한 환경에 함께 설치할 수 없다. 그래서 whisperx 만 별도 venv 에 두고
core_engine 이 이 파일을 서브프로세스로 호출한다.

진행 상황은 stderr, 결과는 --out 으로 지정한 JSON 파일에 쓴다.
"""

import argparse
import json
import os
import sys


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def pick_compute_type(device):
    """VRAM 에 맞는 연산 타입. 3GB 급 카드에서 float16 large-v3 는 OOM 난다."""
    if device != "cuda":
        return "int8"
    try:
        import torch

        free, _ = torch.cuda.mem_get_info()
        return "float16" if free >= 5.5e9 else "int8_float16"
    except Exception:
        return "int8_float16"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hf-token", default="")
    ap.add_argument("--model", default=os.environ.get("SUBEXT_WHISPER_MODEL", "large-v3"))
    ap.add_argument("--device", default="")
    ap.add_argument("--compute-type", default=os.environ.get("SUBEXT_WHISPER_COMPUTE", ""))
    ap.add_argument("--batch-size", type=int, default=int(os.environ.get("SUBEXT_WHISPER_BATCH", "8")))
    a = ap.parse_args()

    import torch
    import whisperx

    device = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    compute_type = a.compute_type or pick_compute_type(device)

    log("   - 장치: %s / 연산 타입: %s / 모델: %s" % (device, compute_type, a.model))
    if device == "cuda":
        try:
            free, total = torch.cuda.mem_get_info()
            log("   - VRAM: %.2fGB 여유 / %.2fGB" % (free / 1e9, total / 1e9))
        except Exception:
            pass

    model = whisperx.load_model(a.model, device, compute_type=compute_type)
    audio = whisperx.load_audio(a.audio)
    result = model.transcribe(audio, batch_size=a.batch_size)
    log("   - 오디오 텍스트화 완료.")

    # 단어 단위 정렬 (화자 분리 정확도를 위해 필요)
    if a.hf_token:
        try:
            align_model, meta = whisperx.load_align_model(
                language_code=result["language"], device=device
            )
            result = whisperx.align(
                result["segments"], align_model, meta, audio, device,
                return_char_alignments=False,
            )
            log("   - 단어 정렬 완료.")
        except Exception as e:
            log("   [경고] 단어 정렬 실패: %s" % e)

        try:
            log("2. 화자 분리(Diarization)를 시작합니다...")
            diarize = whisperx.DiarizationPipeline(use_auth_token=a.hf_token, device=device)
            result = whisperx.assign_word_speakers(diarize(audio), result)
            log("   - 화자 분리 완료.")
        except Exception as e:
            log("   [경고] 화자 분리 중 오류 발생: %s" % e)

    segments = []
    for seg in result.get("segments", []):
        segments.append(
            {
                "start": float(seg.get("start", 0) or 0),
                "end": float(seg.get("end", 0) or 0),
                "text": (seg.get("text") or "").strip(),
                "speaker": seg.get("speaker"),
            }
        )

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "segments": segments,
                "device": device,
                "compute_type": compute_type,
                "model": a.model,
                "language": result.get("language"),
            },
            f,
            ensure_ascii=False,
        )
    log("   - 결과 %d개 구간 저장." % len(segments))


if __name__ == "__main__":
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main()
