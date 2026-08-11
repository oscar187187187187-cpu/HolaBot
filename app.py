import streamlit as st
import requests
import os
import urllib.parse
import textwrap
from groq import Groq
from PIL import Image, ImageDraw, ImageFont
from proglog import ProgressBarLogger

# --- BUGFIX FÜR MOVIEPY (ANTIALIAS) ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import moviepy.video.fx.all as vfx

st.set_page_config(page_title="Faceless Batch Creator", layout="centered")

# --- LIVE-LOGGER FÜR DEN PROZENTBALKEN ---
class StreamlitLogger(ProgressBarLogger):
    def __init__(self, progress_bar, status_text):
        super().__init__()
        self.progress_bar = progress_bar
        self.status_text = status_text

    def bars_callback(self, bar, attr, value, old_value=None):
        total = self.bars[bar]['total']
        if total > 0:
            percent = value / total
            # Das Rendern macht die letzten 50% der Gesamtarbeit aus
            global_percent = 50 + int(percent * 50)
            global_percent = max(1, min(100, global_percent))
            self.progress_bar.progress(global_percent)
            self.status_text.text(f"🎬 Video wird gerendert... {global_percent}% abgeschlossen")

# --- SCHRIFTART HERUNTERLADEN ---
FONT_PATH = "Roboto-Black.ttf"
if not os.path.exists(FONT_PATH):
    font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Black.ttf"
    r = requests.get(font_url)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)

# --- UNTERTITEL: KLEINER UND UNTEN PLATZIERT ---
def create_subtitle_clip(text, duration, video_size=(1080, 1920)):
    wrapped_text = "\n".join(textwrap.wrap(text, width=35)) # Breiter für kleinere Schrift
    
    img = Image.new('RGBA', video_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, 50) # Schrift deutlich verkleinert
    except:
        font = ImageFont.load_default()
        
    # Y-Position: Auf 80% der Bildschirmhöhe gesetzt (untere Hälfte)
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

# --- PUSH BENACHRICHTIGUNG AN DEIN HANDY ---
def send_push_notification(topic, title, message):
    if not topic:
        return
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode('utf-8'),
            headers={
                "Title": title,
                "Priority": "high",
                "Tags": "movie_camera,crown"
            },
            timeout=5
        )
    except Exception as e:
        print(f"Push-Fehler: {e}")


st.title("🎬 Faceless AI Creator")
st.write("Mehrere Dateien hochladen. Live-Ladebalken. Kleine Untertitel.")

groq_key = st.secrets.get("GROQ_API_KEY", "")
if not groq_key:
    groq_key = st.sidebar.text_input("Groq API Key (Gratis)", type="password")
else:
    st.sidebar.success("✅ Groq Key geladen!")

st.sidebar.markdown("---")
st.sidebar.subheader("🔔 Push-Benachrichtigung")
push_topic = st.sidebar.text_input("ntfy-Kanalname:", value="mein-faceless-kanal-99")
st.sidebar.caption("👉 Lade die Gratis-App 'ntfy' aufs Handy und abonniere dort diesen Kanalnamen!")

audio_files = st.file_uploader("Audios hochladen (MP3/WAV)", type=["mp3", "wav"], accept_multiple_files=True)

if st.button("🚀 Videos jetzt produzieren") and audio_files:
    if not groq_key:
        st.error("Bitte hinterlege deinen Groq API Key!")
    else:
        client = Groq(api_key=groq_key)
        
        for idx, audio_file in enumerate(audio_files):
            st.markdown(f"### ⚙️ Verarbeite Video {idx + 1} von {len(audio_files)}: `{audio_file.name}`")
            
            # --- DER 0-100% BALKEN ---
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 10%
                status_text.text("Audio wird hochgeladen...")
                progress_bar.progress(10)
                temp_audio_path = f"temp_audio_{idx}.mp3"
                with open(temp_audio_path, "wb") as f:
                    f.write(audio_file.read())
                    
                # 20%
                status_text.text("KI schreibt Untertitel...")
                progress_bar.progress(20)
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

                # 35%
                status_text.text("KI generiert Bild-Ideen...")
                progress_bar.progress(35)
                
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
                
                # 50%
                status_text.text("Bilder werden heruntergeladen...")
                progress_bar.progress(50)
                
                image_paths = []
                for p_idx, p_text in enumerate(prompts_final):
                    encoded_p = urllib.parse.quote(p_text)
                    img_url = f"https://image.pollinations.ai/prompt/{encoded_p}%20cinematic%20dark%20moody%20faceless%20aesthetic%20vertical%209:16?width=1080&height=1920&nologo=true&seed={p_idx+100+idx}"
                    img_bytes = requests.get(img_url).content
                    img_filename = f"ai_img_{idx}_{p_idx}.png"
                    with open(img_filename, "wb") as img_file:
                        img_file.write(img_bytes)
                    image_paths.append(img_filename)

                # Ab hier übernimmt der Custom Logger (50% bis 100%)
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
                output_path = f"final_faceless_{idx}.mp4"
                
                # Turbo Rendern MIT Live-Ladebalken in VOLLER Qualität
                live_logger = StreamlitLogger(progress_bar, status_text)
                final_bg.write_videofile(
                    output_path, 
                    fps=15, 
                    codec="libx264", 
                    audio_codec="aac",
                    preset="ultrafast", 
                    threads=4,          
                    logger=live_logger  # Live-Ladebalken aktiv!
                )
                
                progress_bar.progress(100)
                status_text.text("✅ Video erfolgreich generiert!")
                
                # Benachrichtigung aufs Handy schicken
                send_push_notification(
                    push_topic, 
                    "🎬 Video Fertig!", 
                    f"Video {idx + 1} ({audio_file.name}) wurde in voller Qualität erstellt!"
                )
                
                with open(output_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ {audio_file.name} herunterladen", 
                        data=f, 
                        file_name=f"faceless_{audio_file.name}.mp4", 
                        mime="video/mp4",
                        key=f"download_{idx}" 
                    )
                    
            except Exception as e:
                st.error(f"Fehler bei Datei {audio_file.name}: {str(e)}")
                
        st.success("🎉 Alle deine Videos sind fertig!")
