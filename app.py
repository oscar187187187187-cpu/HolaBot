import streamlit as st
import requests
import os
import urllib.parse
import textwrap
import threading
from groq import Groq
from PIL import Image, ImageDraw, ImageFont

# --- BUGFIX FÜR MOVIEPY (ANTIALIAS) ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import moviepy.video.fx.all as vfx

st.set_page_config(page_title="Faceless Batch Creator", layout="centered")

# --- SCHRIFTART HERUNTERLADEN ---
FONT_PATH = "Roboto-Black.ttf"
if not os.path.exists(FONT_PATH):
    font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Black.ttf"
    r = requests.get(font_url)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)

# --- UNTERTITEL: KLEINER UND UNTEN PLATZIERT ---
def create_subtitle_clip(text, duration, video_size=(1080, 1920)):
    wrapped_text = "\n".join(textwrap.wrap(text, width=35)) 
    
    img = Image.new('RGBA', video_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, 50) 
    except:
        font = ImageFont.load_default()
        
    y_position = int(video_size[1] * 0.8)
    
    draw.multiline_text(
        (video_size[0]//2, y_position), 
        wrapped_text, 
        font=font, 
        fill="white", 
        stroke_fill="black", 
        stroke_width=4, 
        anchor="mm", 
        align="center"
    )
    
    temp_img_path = f"temp_sub_{hash(text)}.png"
    img.save(temp_img_path)
    return ImageClip(temp_img_path).set_duration(duration)

# --- NEU: PUSH BENACHRICHTIGUNG ---
def send_push_notification(topic: str, message: str):
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode('utf-8'),
            headers={
                "Title": "👑 Faceless Creator",
                "Priority": "high",
                "Tags": "movie_camera,crown"
            },
            timeout=10
        )
    except Exception as e:
        print(f"Push-Fehler: {e}")

# --- NEU: BACKGROUND WORKER (Deine Original-Logik im Hintergrund) ---
def process_videos_in_background(audio_data_list, groq_key, push_topic):
    client = Groq(api_key=groq_key)
    
    send_push_notification(push_topic, f"🚀 Job gestartet! {len(audio_data_list)} Video(s) in Bearbeitung...")
    
    for idx, audio_item in enumerate(audio_data_list):
        audio_name = audio_item["name"]
        audio_bytes = audio_item["bytes"]
        output_path = f"final_faceless_{idx}.mp4"
        
        try:
            # 1. Audio speichern
            temp_audio_path = f"temp_audio_{idx}.mp3"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_bytes)
                
            # 2. KI schreibt Untertitel (Whisper)
            with open(temp_audio_path, "rb") as file:
                whisper_response = client.audio.transcriptions.create(
                    file=(temp_audio_path, file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json"
                )
            segments = whisper_response.segments
            
            if len(segments) > 12:
                combined_segments = []
                step = len(segments) // 12 + 1
                for i in range(0, len(segments), step):
                    chunk = segments[i : i+step]
                    if not chunk: continue
                    combined_segments.append({
                        "start": chunk[0]["start"],
                        "end": chunk[-1]["end"],
                        "text": " ".join([c["text"].strip() for c in chunk])
                    })
                segments = combined_segments[:12]

            # 3. KI generiert Bild-Ideen (Llama 3)
            segments_text_structured = ""
            for s_idx, seg in enumerate(segments):
                segments_text_structured += f"Segment {s_idx+1}: {seg['text'].strip()}\n"

            prompt_request = f"""You are a cinematic director. 
Create exactly {len(segments)} hyper-detailed visual prompts in English for a dark motivational faceless video.
Output ONLY the {len(segments)} prompts, separated by newlines. No intro, no numbers.
Transcript:
"{segments_text_structured}"
"""
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_request}],
                model="llama-3.3-70b-versatile",
            )
            raw_prompts = chat_completion.choices[0].message.content.strip().split("\n")
            prompts_final = [p.strip("- ").strip("1234567890. ") for p in raw_prompts if p.strip()][:len(segments)]
            
            # 4. Bilder werden heruntergeladen (Pollinations)
            image_paths = []
            for p_idx, p_text in enumerate(prompts_final):
                encoded_p = urllib.parse.quote(p_text)
                img_url = f"https://image.pollinations.ai/prompt/{encoded_p}%20cinematic%20dark%20moody%20faceless%20aesthetic%20vertical%209:16?width=1080&height=1920&nologo=true&seed={p_idx+100+idx}"
                img_bytes_dl = requests.get(img_url).content
                img_filename = f"ai_img_{idx}_{p_idx}.png"
                with open(img_filename, "wb") as img_file:
                    img_file.write(img_bytes_dl)
                image_paths.append(img_filename)

            # 5. MoviePy Rendering
            audio_full = AudioFileClip(temp_audio_path)
            video_clips = []
            
            for s_idx, img_p in enumerate(image_paths):
                current_duration = segments[s_idx]["end"] - segments[s_idx]["start"]
                if current_duration <= 0: current_duration = 1.0 
                
                bg_clip = ImageClip(img_p).resize(newsize=(1080, 1920)).set_duration(current_duration)
                bg_zoomed = bg_clip.fx(vfx.resize, lambda t: 1 + 0.15 * (t / current_duration)).set_position('center')
                
                sub_clip = create_subtitle_clip(segments[s_idx]["text"], current_duration)
                comp = CompositeVideoClip([bg_zoomed, sub_clip], size=(1080, 1920)).set_duration(current_duration)
                video_clips.append(comp)
                
            final_bg = concatenate_videoclips(video_clips, method="compose").set_audio(audio_full)
            
            # Logger deaktiviert, da UI nicht blockiert werden soll
            final_bg.write_videofile(
                output_path, 
                fps=15, 
                codec="libx264", 
                audio_codec="aac",
                preset="ultrafast", 
                threads=4,          
                logger=None  
            )
            
        except Exception as e:
            send_push_notification(push_topic, f"❌ Fehler bei Video {idx + 1}: {str(e)}")
            continue
            
    send_push_notification(push_topic, "✅ Alle Videos sind fertig! Kehre in die App zurück, um sie herunterzuladen.")

# --- STREAMLIT UI ---
st.title("🎬 Faceless AI Creator (Background Mode)")
st.write("Videos werden im Hintergrund generiert. Du kannst Safari schließen!")

groq_key = st.secrets.get("GROQ_API_KEY", "")
if not groq_key:
    groq_key = st.sidebar.text_input("Groq API Key (Gratis)", type="password")
else:
    st.sidebar.success("✅ Groq Key geladen!")

push_topic = st.sidebar.text_input("Push-Kanal Name:", value="mein-video-kanal-187")
st.sidebar.info(f"💡 Abonnieren auf: **ntfy.sh/{push_topic}**")

audio_files = st.file_uploader("Audios hochladen (MP3/WAV)", type=["mp3", "wav"], accept_multiple_files=True)

if st.button("🚀 Videos im Hintergrund produzieren") and audio_files:
    if not groq_key:
        st.error("Bitte hinterlege deinen Groq API Key!")
    else:
        # Audios aus dem flüchtigen Streamlit-Speicher in echte Bytes umwandeln
        audio_data_list = [{"name": f.name, "bytes": f.read()} for f in audio_files]
        
        # Thread starten (Fire & Forget)
        thread = threading.Thread(
            target=process_videos_in_background, 
            args=(audio_data_list, groq_key, push_topic)
        )
        thread.start()
        
        st.success("✅ Prozess gestartet! Du kannst die App jetzt schließen.")
        st.info("Du bekommst eine Push-Benachrichtigung mit der Krone 👑, wenn alles fertig ist.")

# --- ABHOLSTATION FÜR FERTIGE VIDEOS ---
st.divider()
st.subheader("📥 Abholstation (Fertige Videos)")
# Sucht nach allen Dateien, die "final_faceless_" heißen
fertige_videos = [f for f in os.listdir() if f.startswith("final_faceless_") and f.endswith(".mp4")]

if not fertige_videos:
    st.write("Noch keine Videos fertig...")
else:
    st.success(f"{len(fertige_videos)} Video(s) stehen zum Download bereit!")
    for vid_file in fertige_videos:
        with open(vid_file, "rb") as f:
            st.download_button(
                label=f"⬇️ {vid_file} herunterladen", 
                data=f, 
                file_name=vid_file, 
                mime="video/mp4",
                key=vid_file 
            )
