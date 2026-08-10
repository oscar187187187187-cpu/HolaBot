import streamlit as st
import requests
import os
import urllib.parse
from groq import Groq
from PIL import Image, ImageDraw
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import moviepy.video.fx.all as vfx

st.set_page_config(page_title="Faceless AI Video Creator", layout="centered")

st.title("🎬 Faceless AI Video Creator (100% Free)")
st.write("Generiert KI-Bilder passend zu deiner Stimme mit Kamera-Zoom.")

# --- Groq Key automatisch laden ---
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
        with st.spinner("KI verarbeitet Audio & generiert Visuals..."):
            
            # 1. Audio temporär speichern
            temp_audio_path = "temp_audio.mp3"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_file.read())
                
            client = Groq(api_key=groq_key)
            
            # 2. Audio Transkribieren via Whisper
            st.info("🎙️ Transkribiere Stimme...")
            with open(temp_audio_path, "rb") as file:
                transcript_text = client.audio.transcriptions.create(
                    file=(temp_audio_path, file.read()),
                    model="whisper-large-v3",
                    response_format="text"
                )
            
            st.success("Transkription fertig!")
            st.write("**Gefundener Text:**", transcript_text)
            
            # 3. Llama 3 generiert 4 passende Bild-Prompts
            st.info("🧠 Llama-3 KI erstellt Bild-Prompts zum Text...")
            prompt_request = f"""Based on this transcript, generate 4 distinct, hyper-detailed visual prompts in English for a cinematic dark motivational faceless video. 
Output ONLY the 4 prompts, separated by newlines. Do not write intro, numbers or explanations.
Transcript: "{transcript_text}"
"""
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_request}],
                model="llama-3.3-70b-versatile",
            )
            
            raw_prompts = chat_completion.choices[0].message.content.strip().split("\n")
            prompts = [p.strip("- ").strip("1234567890. ") for p in raw_prompts if p.strip()][:4]
            
            # 4. Kostenlose KI-Bilder via Pollinations.ai erstellen
            st.info("🎨 KI generiert 9:16 Faceless-Bilder...")
            image_paths = []
            for idx, p_text in enumerate(prompts):
                encoded_p = urllib.parse.quote(p_text)
                # 1080x1920 Vertikalformat im düsteren Cinematic-Stil
                img_url = f"https://image.pollinations.ai/prompt/{encoded_p}%20cinematic%20dark%20moody%20faceless%20aesthetic%209:16?width=1080&height=1920&nologo=true&seed={idx+15}"
                
                img_bytes = requests.get(img_url).content
                img_filename = f"ai_img_{idx}.png"
                with open(img_filename, "wb") as img_file:
                    img_file.write(img_bytes)
                image_paths.append(img_filename)
                
            # 5. Videoschnitt mit Ken-Burns Zoom-Effekt
            st.info("🎬 Animiere Bilder mit Zoom-Effekt & schneide Video...")
            audio = AudioFileClip(temp_audio_path)
            total_duration = audio.duration
            duration_per_img = total_duration / len(image_paths)
            
            video_clips = []
            for img_p in image_paths:
                img_clip = ImageClip(img_p).set_duration(duration_per_img)
                
                # Zoom-Animation von 1.0 auf 1.15 Skalierung
                zoomed = img_clip.fx(vfx.resize, lambda t: 1 + 0.15 * (t / duration_per_img))
                comp = CompositeVideoClip([zoomed.set_position('center')], size=(1080, 1920)).set_duration(duration_per_img)
                video_clips.append(comp)
                
            final_bg = concatenate_videoclips(video_clips, method="compose").set_audio(audio)
            
            # Untertitel / Banner-Overlay
            text_img_path = "text_overlay.png"
            img = Image.new('RGBA', (600, 120), color=(0, 0, 0, 180))
            draw = ImageDraw.Draw(img)
            draw.text((50, 45), "🔊 Sound On | Deep Mindset", fill="white")
            img.save(text_img_path)
            
            txt_clip = ImageClip(text_img_path).set_position(('center', 1500)).set_duration(total_duration)
            
            final_video = CompositeVideoClip([final_bg, txt_clip])
            output_path = "final_faceless_video.mp4"
            
            final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
            
            st.success("🎉 Dein Faceless KI-Video ist fertig!")
            
            # 6. Download Button
            with open(output_path, "rb") as f:
                st.download_button("⬇️ Video auf iPhone speichern", f, file_name="faceless_video.mp4", mime="video/mp4")
