import streamlit as st
import requests
import os
import urllib.parse
from groq import Groq
from PIL import Image, ImageDraw

# --- BUGFIX FÜR MOVIEPY (Ken-Burns-Zoom) ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import moviepy.video.fx.all as vfx

st.set_page_config(page_title="Faceless AI Video Creator", layout="centered")

# --- STREAMLIT GEDÄCHTNIS ---
if "video_ready" not in st.session_state:
    st.session_state.video_ready = False
if "video_path" not in st.session_state:
    st.session_state.video_path = ""

st.title("🎬 Faceless AI Video Creator (Turbo & Fullscreen)")
st.write("Generiert 8 hochauflösende KI-Bilder mit Kamera-Zoom.")

groq_key = st.secrets.get("GROQ_API_KEY", "")

if not groq_key:
    st.sidebar.header("API Schlüssel")
    groq_key = st.sidebar.text_input("Groq API Key (Gratis)", type="password")
else:
    st.sidebar.success("✅ Groq Key geladen!")

audio_file = st.file_uploader("Audio hochladen (MP3/WAV)", type=["mp3", "wav"])

if st.button("🚀 Faceless Video generieren") and audio_file:
    if not groq_key:
        st.error("Bitte hinterlege deinen Groq API Key!")
    else:
        st.session_state.video_ready = False 
        
        with st.spinner("KI verarbeitet Audio & generiert 8 Bilder..."):
            
            temp_audio_path = "temp_audio.mp3"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_file.read())
                
            client = Groq(api_key=groq_key)
            
            st.info("🎙️ Transkribiere Stimme...")
            with open(temp_audio_path, "rb") as file:
                transcript_text = client.audio.transcriptions.create(
                    file=(temp_audio_path, file.read()),
                    model="whisper-large-v3",
                    response_format="text"
                )
            
            # --- MEHR BILDER: 8 Prompts statt 4 ---
            st.info("🧠 Llama-3 KI erstellt 8 Bild-Prompts zum Text...")
            prompt_request = f"""Based on this transcript, generate 8 distinct, hyper-detailed visual prompts in English for a cinematic dark motivational faceless video. 
Output ONLY the 8 prompts, separated by newlines. Do not write intro, numbers or explanations.
Transcript: "{transcript_text}"
"""
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_request}],
                model="llama-3.3-70b-versatile",
            )
            
            raw_prompts = chat_completion.choices[0].message.content.strip().split("\n")
            prompts = [p.strip("- ").strip("1234567890. ") for p in raw_prompts if p.strip()][:8]
            
            st.info("🎨 KI generiert 8 vertikale Fullscreen-Bilder...")
            image_paths = []
            for idx, p_text in enumerate(prompts):
                encoded_p = urllib.parse.quote(p_text)
                img_url = f"https://image.pollinations.ai/prompt/{encoded_p}%20cinematic%20dark%20moody%20faceless%20aesthetic%20vertical%209:16?width=1080&height=1920&nologo=true&seed={idx+50}"
                
                img_bytes = requests.get(img_url).content
                img_filename = f"ai_img_{idx}.png"
                with open(img_filename, "wb") as img_file:
                    img_file.write(img_bytes)
                image_paths.append(img_filename)
                
            st.info("🎬 Rendere Video mit Turbo-Modus... (Das geht jetzt deutlich schneller!)")
            audio = AudioFileClip(temp_audio_path)
            total_duration = audio.duration
            duration_per_img = total_duration / len(image_paths)
            
            video_clips = []
            for img_p in image_paths:
                # --- VOLLBILD-GARANTIE: Bild wird hart auf 1080x1920 skaliert ---
                img_clip = ImageClip(img_p).resize(newsize=(1080, 1920)).set_duration(duration_per_img)
                
                # Zoom-Effekt
                zoomed = img_clip.fx(vfx.resize, lambda t: 1 + 0.15 * (t / duration_per_img))
                comp = CompositeVideoClip([zoomed.set_position('center')], size=(1080, 1920)).set_duration(duration_per_img)
                video_clips.append(comp)
                
            final_bg = concatenate_videoclips(video_clips, method="compose").set_audio(audio)
            
            text_img_path = "text_overlay.png"
            img = Image.new('RGBA', (600, 120), color=(0, 0, 0, 180))
            draw = ImageDraw.Draw(img)
            draw.text((50, 45), "🔊 Sound On | Deep Mindset", fill="white")
            img.save(text_img_path)
            
            txt_clip = ImageClip(text_img_path).set_position(('center', 1500)).set_duration(total_duration)
            
            final_video = CompositeVideoClip([final_bg, txt_clip])
            output_path = "final_faceless_video.mp4"
            
            # --- SPEED-HACK: fps auf 15 reduziert für 40% schnelleres Rendern ---
            final_video.write_videofile(
                output_path, 
                fps=15, 
                codec="libx264", 
                audio_codec="aac",
                preset="ultrafast", 
                threads=4,          
                logger=None         
            )
            
            st.session_state.video_path = output_path
            st.session_state.video_ready = True
            
            st.success("🎉 Dein schnelles Faceless KI-Video ist fertig!")

if st.session_state.video_ready and os.path.exists(st.session_state.video_path):
    st.markdown("### Dein Video ist bereit zum Download!")
    with open(st.session_state.video_path, "rb") as f:
        st.download_button(
            label="⬇️ Video auf iPhone speichern", 
            data=f, 
            file_name="faceless_video_turbo.mp4", 
            mime="video/mp4"
        )
