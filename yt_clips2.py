import gradio as gr
from clip_maker2 import generate_clips  # suppose you moved the main logic into a function

def process_url(url):
    clips = generate_clips(url)  # returns a list of clip file paths
    return clips  # Gradio will show videos if outputs=gr.Video()

demo = gr.Interface(
    fn=process_url,
    inputs=gr.Textbox(label="YouTube URL"),
    outputs=[gr.Video(label=f"Clip {i+1}") for i in range(3)],
    title="🎥 AI-Powered YouTube Clip Generator",
    description="Enter a YouTube URL — get the top 3 emotional moments automatically!",
)

demo.launch()
