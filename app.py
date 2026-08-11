import streamlit as st
import requests
import os
import urllib.parse
import textwrap
from groq import Groq
from PIL import Image, ImageDraw, ImageFont

# --- BUGFIX FÜR MOVIEPY (ANTIALIAS) ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import moviepy.video.fx.all as vfx

st.set_page_config(page_title="Faceless Batch Creator", layout="centered")

# --- SCHRIFTART FÜR UNTERTITEL HERUNTERLADEN ---
# Da Streamlit keine coolen Schriftarten hat, laden wir eine fette Social-Media-Schrift (Roboto Black)
FONT_PATH = "Roboto-Black.ttf"
if not os.path.exists(FONT_PATH):
    font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Black.ttf"
    r = requests.get(font_url)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)

# Funktion für dynamische Untertitel-Bilder (Transparent)
def create_subtitle_clip(text, duration, video_size=(1080, 1920)):
    # Text umbrechen, damit er nicht aus dem Bildschirm ragt
    wrapped_text = "\n".join(textwrap.wrap(text, width=25))
    
    img = Image.new('RGBA', video_size, (0, 0, 0, 0)) # Komplett transparent
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, 80) # Sehr große, fette Schrift
    except:
        font = ImageFont.load_default()
        
    # Text zentriert zeichnen mit schwarzer, dicker Umrandung (Outline) für Lesbarkeit
    draw.multiline_text(
        (video_size[0]//2, video_size[1]//2), 
        wrapped_text, 
        font=font, 
        fill="white", 
        stroke_fill="black", 
        stroke_width=6, 
        anchor="mm", 
        align="center"
    )
    
    temp_img_path = f"temp_sub_{hash(text)}.png"
    img.save(temp_img_path)
    return ImageClip(temp_img_path).set_duration(duration)


st.title("🎬 Faceless AI Creator (Batch & Subtitles)")
st.write("Mehrere Dateien hochladen. Dynamische Untertitel. Maximale Qualität.")

groq_key = st.secrets.get("GROQ_API_KEY", "")
if not groq_key:
    groq_key = st.sidebar.text_input("Groq API Key (Gratis)", type="password")
else:
    st.sidebar.success("✅ Groq Key geladen!")

# --- MEHRERE DATEIEN HOCHLADEN (BATCH) ---
audio_files = st.file_uploader("Audios hochladen (MP3/WAV) - Mehrere erlaubt!", type=["mp3", "wav"], accept_multiple_files=True)

if st.button("🚀 Videos jetzt produzieren") and audio_files:
    if not groq_key:
        st.error("Bitte hinterlege deinen Groq API Key!")
    else:
        client = Groq(api_key=groq_key)
        
        # Schleife über alle hochgeladenen Dateien
        for idx, audio_file in enumerate(audio_files):
            st.markdown(f"### ⚙️ Verarbeite Video {idx + 1} von {len(audio_files)}: `{audio_file.name}`")
            
            # --- 0-100% LADEBALKEN ---
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Schritt 1: Speichern (10%)
                status_text.text("Schritt 1/5: Audio wird vorbereitet...")
                progress_bar.progress(10)
                temp_audio_path = f"temp_audio_{idx}.mp3"
                with open(temp_audio_path, "wb") as f:
                    f.write(audio_file.read())
                    
                # Schritt 2: Whisper Transkription (30%)
                status_text.text("Schritt 2/5: Whisper transkribiert (mit Zeitstempeln)...")
                progress_bar.progress(30)
                with open(temp_audio_path, "rb") as file:
                    whisper_response = client.audio.transcriptions.create(
                        file=(temp_audio_path, file.read()),
                        model="whisper-large-v3",
                        response_format="verbose_json"
                    )
                segments = whisper_response.segments
                
                # Cloud-Limitierung auf max 12 Segmente (damit der Server nicht crasht)
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

                # Schritt 3: Llama-3 Prompts mit DOUBLE-CHECK (50%)
                status_text.text("Schritt 3/5: KI generiert & prüft Bild-Prompts (Double-Check)...")
                progress_bar.progress(50)
                
                segments_text_structured = ""
                for s_idx, seg in enumerate(segments):
                    segments_text_structured += f"Segment {s_idx+1}: {seg['text'].strip()}\n"

                # Der neue "Double-Check" Prompt
                prompt_request = f"""You are a cinematic director. 
Task: 
1. Create exactly {len(segments)} hyper-detailed visual prompts in English for a dark motivational faceless video based on the segments below.
2. DOUBLE-CHECK: Review your prompts. Ensure they perfectly match the semantic meaning of the text. If the text talks about 'success', show climbing or victory. If it talks about 'pain', show struggle.
3. Output ONLY the {len(segments)} final validated prompts, separated by newlines. No intro, no numbers.
Transcript:
"{segments_text_structured}"
"""
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_request}],
                    model="llama-3.3-70b-versatile",
                )
                raw_prompts = chat_completion.choices[0].message.content.strip().split("\n")
                prompts_final = [p.strip("- ").strip("1234567890. ") for p in raw_prompts if p.strip()][:len(segments)]
                
                # Schritt 4: KI Bilder laden (70%)
                status_text.text("Schritt 4/5: KI lädt hochauflösende Visuals herunter...")
                progress_bar.progress(70)
                
                image_paths = []
                for p_idx, p_text in enumerate(prompts_final):
                    encoded_p = urllib.parse.quote(p_text)
                    img_url = f"https://image.pollinations.ai/prompt/{encoded_p}%20cinematic%20dark%20moody%20faceless%20aesthetic%20vertical%209:16?width=1080&height=1920&nologo=true&seed={p_idx+100+idx}"
                    img_bytes = requests.get(img_url).content
                    img_filename = f"ai_img_{idx}_{p_idx}.png"
                    with open(img_filename, "wb") as img_file:
                        img_file.write(img_bytes)
                    image_paths.append(img_filename)

                # Schritt 5: Videoschnitt & Untertitel (90% - dauert am längsten)
                status_text.text("Schritt 5/5: Rendere Video mit dynamischen Untertiteln (Turbo-Modus)...")
                progress_bar.progress(90)
                
                audio_full = AudioFileClip(temp_audio_path)
                video_clips = []
                
                for s_idx, img_p in enumerate(image_paths):
                    # Dauer berechnen
                    current_duration = segments[s_idx]["end"] - segments[s_idx]["start"]
                    if current_duration <= 0: current_duration = 1.0 # Fallback
                    
                    # 1. Das Hintergrundbild (Vollbild + Ken Burns Zoom)
                    bg_clip = ImageClip(img_p).resize(newsize=(1080, 1920)).set_duration(current_duration)
                    bg_zoomed = bg_clip.fx(vfx.resize, lambda t: 1 + 0.15 * (t / current_duration)).set_position('center')
                    
                    # 2. Der dynamische Untertitel für dieses Segment
                    sub_clip = create_subtitle_clip(segments[s_idx]["text"], current_duration)
                    
                    # Zusammenfügen
                    comp = CompositeVideoClip([bg_zoomed, sub_clip], size=(1080, 1920)).set_duration(current_duration)
                    video_clips.append(comp)
                    
                final_bg = concatenate_videoclips(video_clips, method="compose").set_audio(audio_full)
                
                output_path = f"final_faceless_{idx}.mp4"
                
                # Turbo Rendern
                final_bg.write_videofile(
                    output_path, 
                    fps=15, 
                    codec="libx264", 
                    audio_codec="aac",
                    preset="ultrafast", 
                    threads=4,          
                    logger=None         
                )
                
                # FERTIG (100%)
                progress_bar.progress(100)
                status_text.text("✅ Video erfolgreich generiert!")
                
                # Download Button für dieses spezifische Video anzeigen
                with open(output_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ {audio_file.name} herunterladen", 
                        data=f, 
                        file_name=f"faceless_{audio_file.name}.mp4", 
                        mime="video/mp4",
                        key=f"download_{idx}" # Wichtig für Streamlit (eindeutiger Button pro Video)
                    )
                    
            except Exception as e:
                st.error(f"Fehler bei Datei {audio_file.name}: {str(e)}")
                
        st.success("🎉 Alle deine Videos sind fertig!")
