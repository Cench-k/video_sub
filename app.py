import gradio as gr
import cv2
import numpy as np
from core_engine import process_audio


def extract_frame(file_obj):
    """업로드된 영상에서 30% 지점 프레임 추출."""
    if file_obj is None:
        return None
    path = file_obj.name if hasattr(file_obj, "name") else file_obj
    cap = cv2.VideoCapture(path)
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * 0.3))
    ret, frame = cap.read()
    cap.release()
    if ret:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return None


def preview_crop(frame_img, top, bottom, left, right):
    """슬라이더 값에 따라 선택 영역을 초록 박스로 표시."""
    if frame_img is None:
        return None
    img = np.array(frame_img).copy()
    h, w = img.shape[:2]
    y1 = int(h * top / 100)
    y2 = int(h * bottom / 100)
    x1 = int(w * left / 100)
    x2 = int(w * right / 100)
    overlay = img.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 220, 0), -1)
    img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 220, 0), 2)
    return img


def on_analyze(file_obj, selected_model, hf_token, top, bottom, left, right):
    if file_obj is None:
        return "영상 파일을 먼저 업로드해주세요."
    path = file_obj.name if hasattr(file_obj, "name") else file_obj
    crop = (top, bottom, left, right)
    return process_audio(path, selected_model, hf_token, crop=crop)


def on_upload(file_obj, top, bottom, left, right):
    """영상 업로드 시 프레임 미리보기 + 크롭 박스 표시."""
    frame = extract_frame(file_obj)
    return preview_crop(frame, top, bottom, left, right), frame


# ===== UI =====
with gr.Blocks(title="도우인 & 웹 영상 자막 추출기") as demo:
    gr.Markdown("# 🎙️ 로컬 자동 화자분리 및 자막 추출 (SenseVoice & WhisperX)")
    gr.Markdown("> 영상을 업로드하고 자막 영역을 맞춘 뒤 **분석 시작**을 누르세요.")

    # 원본 프레임 (숨김 상태로 슬라이더 연동에 사용)
    raw_frame = gr.State(None)

    with gr.Row():
        # ── 왼쪽: 설정 ──────────────────────────────────────────────────────
        with gr.Column(scale=1):
            model_selector = gr.Dropdown(
                label="AI 모델 선택",
                choices=[
                    ("🔀 음성 + 하드자막 병합 (권장)", "combined"),
                    ("🎙️ 음성 전용 (SenseVoice)", "sensevoice"),
                    ("🎙️ 음성 전용 (WhisperX)", "whisperx"),
                ],
                value="combined",
                info="병합 모드: 하드자막 우선, 음성은 자막 없는 구간 보완",
            )
            token_input = gr.Textbox(
                label="HuggingFace Token (선택)",
                placeholder="WhisperX 화자 분리 전용 토큰",
                type="password",
            )

            gr.Markdown("### 자막 영역 설정")
            gr.Markdown("영상 업로드 후 슬라이더로 초록 박스를 자막 위치에 맞추세요.")

            crop_top = gr.Slider(0, 100, value=70, step=1, label="위쪽 경계 (%)")
            crop_bottom = gr.Slider(0, 100, value=100, step=1, label="아래쪽 경계 (%)")
            crop_left = gr.Slider(0, 100, value=0, step=1, label="왼쪽 경계 (%)")
            crop_right = gr.Slider(0, 100, value=100, step=1, label="오른쪽 경계 (%)")

            analyze_btn = gr.Button("▶ 분석 시작", variant="primary")

        # ── 오른쪽: 영상 업로드 + 프레임 미리보기 ─────────────────────────
        with gr.Column(scale=2):
            audio_upload = gr.File(
                label="영상(MP4) 또는 음성 파일 업로드 📥",
                file_count="single",
            )
            frame_preview = gr.Image(
                label="자막 영역 미리보기 (초록 박스 = 선택된 영역)",
                interactive=False,
                height=300,
            )

    result_output = gr.Textbox(
        label="자막 및 화자분리 결과",
        lines=15,
        placeholder="이곳에 결과가 출력됩니다...",
    )

    # ── 이벤트 ────────────────────────────────────────────────────────────
    # 영상 업로드 → 프레임 추출 + 크롭 박스 표시
    audio_upload.change(
        fn=on_upload,
        inputs=[audio_upload, crop_top, crop_bottom, crop_left, crop_right],
        outputs=[frame_preview, raw_frame],
    )

    # 슬라이더 변경 → 크롭 박스 실시간 업데이트
    for slider in [crop_top, crop_bottom, crop_left, crop_right]:
        slider.change(
            fn=preview_crop,
            inputs=[raw_frame, crop_top, crop_bottom, crop_left, crop_right],
            outputs=frame_preview,
        )

    # 분석 시작 버튼
    analyze_btn.click(
        fn=on_analyze,
        inputs=[audio_upload, model_selector, token_input,
                crop_top, crop_bottom, crop_left, crop_right],
        outputs=result_output,
    )


if __name__ == "__main__":
    print("Local Web Server Initializing...")
    demo.launch(inbrowser=True, theme=gr.themes.Soft())
