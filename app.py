import streamlit as st
import requests
import os
from groq import Groq
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

st.set_page_config(page_title="Social Video Creator", layout="centered")

st.title("🎬 1-Min+ Video Creator (Mobil & Free)")
st.write("Erstelle aus deinem Audio ein fertiges Social-Media-Video.")

# Einstellungen in der Seitenleiste
st.sidebar.header("API Schlüssel")
groq_key = st.sidebar.text_input("Groq API Key (Gratis)", type="password")
pexels_key = st.sidebar.text_input("Pexels API Key (Gratis)", type="password")

audio_file = st.file_uploader("Audio hochladen (MP3/WAV)", type=["mp3", "wav"])
search_keyword = st.text_input("Suchbegriff für Hintergrundvideo", "nature")

if st.button("🚀 Video jetzt generieren") and audio_file:
    if not groq_key or not pexels_key:
        st.error("Bitte gib zuerst beide API-Key in der Seitenleiste ein!")
    else:
        with st.spinner("Server verarbeitet dein Video... Bitte Seite nicht schließen!"):
            
            # 1. Audio speichern
            temp_audio_path = "temp_audio.mp3"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_file.read())
                
            # 2. Transkribieren via Groq (100% Kostenfrei & Blitzschnell)
            st.info("Transkribiere Audio mit Groq Whisper...")
            client = Groq(api_key=groq_key)
            
            with open(temp_audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(temp_audio_path, file.read()),
                    model="whisper-large-v3",
                    response_format="text"
                )
            
            st.success("Transkription fertig!")
            st.write("**Erkannter Text:**", transcription)
            
            # 3. Pexels Video laden
            st.info("Lade passendes Video von Pexels...")
            headers = {"Authorization": pexels_key}
            url = f"https://api.pexels.com/videos/search?query={search_keyword}&orientation=portrait&size=hd&per_page=1"
            response = requests.get(url, headers=headers).json()
            
            if "videos" in response and len(response["videos"]) > 0:
                video_url = response["videos"][0]["video_files"][0]["link"]
                video_data = requests.get(video_url).content
                
                temp_video_path = "temp_video.mp4"
                with open(temp_video_path, "wb") as v_file:
                    v_file.write(video_data)
                
                # 4. Rendern
                st.info("Rendere finales MP4 Video...")
                bg = VideoFileClip(temp_video_path)
                audio = AudioFileClip(temp_audio_path)
                
                duration = audio.duration
                bg_looped = bg.loop(duration=duration).set_audio(audio)
                
                txt_clip = TextClip("Sound on 🔊", fontsize=50, color='white', font='Arial-Bold', stroke_color='black', stroke_width=2)
                txt_clip = txt_clip.set_position('center').set_duration(duration)
                
                final_video = CompositeVideoClip([bg_looped, txt_clip])
                output_path = "final_output.mp4"
                final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
                
                st.success("🎉 Dein Video ist fertig!")
                
                # 5. Download auf das iPhone
                with open(output_path, "rb") as f:
                    st.download_button("⬇️ Video auf iPhone speichern", f, file_name="social_video.mp4", mime="video/mp4")
            else:
                st.error("Kein Video auf Pexels für diesen Suchbegriff gefunden.")
