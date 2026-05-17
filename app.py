import gradio as gr
import os
from core_engine import process_audio

def on_file_dropped(file_obj, selected_model, hf_token):
    """
    Gradio 웹 UI에서 파일을 올리는 순간 이 콜백 스크립트가 실행됩니다.
    file_obj.name 경로를 읽어서 core_engine에 전달합니다.
    """
    if file_obj is None:
        return ""
    
    # Gradio 버전에 따라 file_obj의 속성이 배열일 수도 있고 단일 객체일수도 있음.
    # 단일 업로더 기준:
    file_path = file_obj.name if hasattr(file_obj, 'name') else file_obj
    
    # AI 구동 및 결과 리턴
    return process_audio(file_path, selected_model, hf_token)

# ===== UI 레이아웃 설계 =====
with gr.Blocks(title="도우인 & 웹 영상 자막 추출기") as demo:
    gr.Markdown("# 🎙️ 로컬 자동 화자분리 및 자막 추출 (SenseVoice & WhisperX)")
    gr.Markdown("> 원하시는 영상을 네모 박스에 **던져 넣으면 시작 버튼 누를 필요 없이 즉시 AI 분석이 시작**됩니다.")
    
    with gr.Row():
        with gr.Column(scale=1):
            # 설정 패널
            model_selector = gr.Dropdown(
                label="AI 모델 선택",
                choices=[
                    ("🔀 음성 + 하드자막 병합 (권장)", "combined"),
                    ("🎙️ 음성 전용 (SenseVoice)", "sensevoice"),
                    ("🎙️ 음성 전용 (WhisperX)", "whisperx"),
                ],
                value="combined",
                info="병합 모드: 음성 인식 공백은 화면 자막으로 자동 보완"
            )
            token_input = gr.Textbox(
                label="HuggingFace Token (선택)", 
                placeholder="WhisperX 화자 분리 전용 토큰", 
                type="password",
                info="FunASR(SenseVoice)는 토큰 없이도 동작합니다."
            )
            
            gr.Markdown("💡 **Tip:** SenseVoice를 선택한 상태에서 파일을 우측에 드래그 앤 드롭해 보세요!")
            
        with gr.Column(scale=2):
            # 파일 업로드 (드래그 앤 드롭 영역)
            audio_upload = gr.File(
                label="여기에 영상(MP4) 또는 음성 파일을 던져주세요 📥", 
                file_count="single"
            )
            
    # 결과가 뜨는 큰 텍스트 박스
    result_output = gr.Textbox(
        label="자막 및 화자분리 결과", 
        lines=15, 
        placeholder="이곳에 결과가 출력됩니다..."
    )

    # 🔗 이벤트 바인딩 (핵심: 오디오 박스 내용물이 변할 때 = 파일이 올라갈 때 자동 실행)
    audio_upload.change(
        fn=on_file_dropped,
        inputs=[audio_upload, model_selector, token_input],
        outputs=result_output
    )

if __name__ == "__main__":
    print("Local Web Server Initializing...")
    demo.launch(inbrowser=True, theme=gr.themes.Soft())
