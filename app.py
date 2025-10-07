# ==============================
# 🎥 AI-Powered Auto Clip Generator
# ==============================
# Install dependencies (run once)
!pip install openai-whisper yt-dlp webvtt-py transformers torch --quiet

import os
import re
import subprocess
import yt_dlp
import whisper
import webvtt
from transformers import pipeline

# ==============================
# 1️⃣ USER INPUT
# ==============================
url = input("Enter YouTube URL: ").strip()

video_file = "video.mp4"
sub_file = "video.en.vtt"

# ==============================
# 2️⃣ DOWNLOAD VIDEO
# ==============================
print("⬇️ Downloading video...")
ydl_opts = {"format": "mp4", "outtmpl": "video.%(ext)s"}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])

# ==============================
# 3️⃣ GENERATE SUBTITLES USING WHISPER
# ==============================
print("🎤 Generating subtitles with Whisper...")
model = whisper.load_model("base")
result = model.transcribe(video_file)

with open(sub_file, "w", encoding="utf-8") as f:
    f.write("WEBVTT\n\n")
    for i, seg in enumerate(result["segments"]):
        start, end, text = seg["start"], seg["end"], seg["text"].strip()
        def sec_to_vtt(s):
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            sec = s % 60
            return f"{h:02}:{m:02}:{sec:06.3f}"
        f.write(f"{i+1}\n{sec_to_vtt(start)} --> {sec_to_vtt(end)}\n{text}\n\n")

print("✅ Subtitles saved as video.en.vtt")

# ==============================
# 4️⃣ GROUP INTO SENTENCE CHUNKS
# ==============================
print("🧩 Creating text chunks...")
grouped_chunks = []
current_chunk, chunk_start, chunk_end = [], None, None
max_chunk_duration, min_chunk_duration = 25.0, 10.0

for caption in webvtt.read(sub_file):
    start_sec = sum(float(x) * 60 ** i for i, x in enumerate(reversed(caption.start.split(":"))))
    end_sec = sum(float(x) * 60 ** i for i, x in enumerate(reversed(caption.end.split(":"))))
    if chunk_start is None:
        chunk_start = start_sec

    sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', caption.text) if s.strip()]

    for sentence in sentences:
        current_chunk.append(sentence)
        chunk_end = end_sec
        if chunk_end - chunk_start >= max_chunk_duration:
            if grouped_chunks and (chunk_end - chunk_start < min_chunk_duration):
                grouped_chunks[-1]["end"] = chunk_end
                grouped_chunks[-1]["text"] += " " + " ".join(current_chunk)
            else:
                grouped_chunks.append({
                    "start": chunk_start,
                    "end": chunk_end,
                    "text": " ".join(current_chunk)
                })
            current_chunk, chunk_start, chunk_end = [], None, None

if current_chunk:
    if grouped_chunks and (chunk_end - chunk_start < min_chunk_duration):
        grouped_chunks[-1]["end"] = chunk_end
        grouped_chunks[-1]["text"] += " " + " ".join(current_chunk)
    else:
        grouped_chunks.append({
            "start": chunk_start,
            "end": chunk_end,
            "text": " ".join(current_chunk)
        })

print(f"✅ Total chunks created: {len(grouped_chunks)}")

# ==============================
# 5️⃣ ANALYZE EMOTION + SENTIMENT
# ==============================
print("🧠 Analyzing emotion and sentiment...")
sentiment_model = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")
emotion_model = pipeline("text-classification",
                         model="joeddav/distilbert-base-uncased-go-emotions-student",
                         return_all_scores=True)

scored_chunks = []
for chunk in grouped_chunks:
    text = chunk["text"]
    sentiment = sentiment_model(text[:512])[0]
    emotions = emotion_model(text[:512])[0]
    top_emotion = max(emotions, key=lambda x: x['score'])
    score = sentiment['score'] * 5
    if top_emotion['label'] in ["joy", "excitement", "anger", "sadness"]:
        score += top_emotion['score'] * 5
    scored_chunks.append({
        "start": chunk["start"],
        "end": chunk["end"],
        "text": text,
        "sentiment": sentiment['label'],
        "emotion": top_emotion['label'],
        "score": score
    })

# ==============================
# 6️⃣ SELECT TOP 3 CLIPS
# ==============================
scored_chunks = sorted(scored_chunks, key=lambda x: x["score"], reverse=True)
top3 = scored_chunks[:3]

print("\n🔥 Top 3 Engaging Moments:")
for i, c in enumerate(top3, 1):
    print(f"\n--- Clip {i} ---")
    print(f"Time: {c['start']:.2f}s → {c['end']:.2f}s")
    print(f"Emotion: {c['emotion']} | Sentiment: {c['sentiment']} | Score: {c['score']:.2f}")
    print(f"Text: {c['text'][:150]}...")

# ==============================
# 7️⃣ EXTRACT CLIPS + SUBTITLES
# ==============================
print("\n✂️ Extracting top 3 clips...")
captions = list(webvtt.read(sub_file))

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')

for i, clip in enumerate(top3, 1):
    start, end = clip["start"], clip["end"]
    out_video, out_sub = f"clip_{i}.mp4", f"clip_{i}.vtt"

    # Extract video
    cmd = ["ffmpeg", "-y", "-i", video_file, "-ss", str(start), "-to", str(end), "-c", "copy", out_video]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Extract subtitles for the clip
    selected = []
    for c in captions:
        start_sec = sum(float(x) * 60 ** i for i, x in enumerate(reversed(c.start.split(":"))))
        end_sec = sum(float(x) * 60 ** i for i, x in enumerate(reversed(c.end.split(":"))))
        if start_sec >= start and end_sec <= end:
            new_start, new_end = start_sec - start, end_sec - start
            selected.append(f"{format_time(new_start)} --> {format_time(new_end)}\n{c.text}\n")

    with open(out_sub, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n" + "\n".join(selected))

    print(f"✅ Saved: {out_video} + {out_sub}")

print("\n🎉 Done! Your top 3 clips and subtitles are ready.")
