import streamlit as st
import requests
import os
import urllib.parse
from groq import Groq
from PIL import Image, ImageDraw, ImageFont

# --- BUGFIX FÜR MOVIEPY (ANTIALIAS) ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import moviepy.video.fx.all as vfx

st.set_page_config(page_title="Faceless AI Creator 2.0", layout="centered")

# --- STREAMLIT GEDÄCHTNIS ---
if "video_ready" not in st.session_state:
    st.session_state.video_ready = False
if "video_path" not in st.session_state:
    st.session_state.video_path = ""

st.title("🎬 Faceless AI Creator 2.0 (Dynamisch)")
st.write("Verbessert: Dynamische Bilder-Synchronisation & transparente Leiste.")

groq_key = st.secrets.get("GROQ_API_KEY", "")

if not groq_key:
    st.sidebar.header("API Schlüssel")
    groq_key = st.sidebar.text_input("Groq API Key (Gratis)", type="password")
else:
    st.sidebar.success("✅ Groq Key geladen!")

audio_file = st.file_uploader("Audio hochladen (MP3/WAV)", type=["mp3", "wav"])

if st.button("🚀 Verbessertes Video generieren") and audio_file:
    if not groq_key:
        st.error("Bitte hinterlege deinen Groq API Key!")
    else:
        # Reset des Gedächtnisses
        st.session_state.video_ready = False 
        
        with st.spinner("KI verarbeitet Audio & synchronisiert Visuals..."):
            
            temp_audio_path = "temp_audio.mp3"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_file.read())
                
            client = Groq(api_key=groq_key)
            
            # 1. WHISPER-SEGMENATION: Verbose JSON liefert Zeitstempel!
            st.info("🎙️ Whisper transkribiert mit Zeitstempeln...")
            with open(temp_audio_path, "rb") as file:
                # Nutze 'verbose_json' für Segmente (Start, End, Text)
                whisper_response = client.audio.transcriptions.create(
                    file=(temp_audio_path, file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json"
                )
            
            # Segmente extrahieren
            segments = whisper_response.segments
            st.success(f"Transkription fertig! {len(segments)} Gedanken/Sätze erkannt.")
            
            # --- TURBO-OPITMIERUNG FÜR CLOUD-RAM-LIMITS ---
            # Begrenze die Anzahl der Segmente auf max. 12 (für 1 Minute).
            # Sonst überlastet das Rendern von 1080p Ken-Burns den Server.
            if len(segments) > 12:
                # Kombiniere Segmente, falls zu viele. (Sehr simpele Logik)
                combined_segments = []
                step = len(segments) // 12 + 1
                for i in range(0, len(segments), step):
                    chunk = segments[i : i+step]
                    if not chunk: continue
                    new_seg = {
                        "start": chunk[0]["start"],
                        "end": chunk[-1]["end"],
                        "text": " ".join([c["text"].strip() for c in chunk])
                    }
                    combined_segments.append(new_seg)
                segments = combined_segments[:12] # Hartes Limit

            # 2. BILD-PROMPTS GENERIEREN (Dynamisch pro Segment)
            st.info(f"🧠 Llama-3 generiert {len(segments)} passende Bilder-Prompts...")
            
            image_paths = []
            segment_durations = []
            
            # Wir machen EINEN Groq-Aufruf, um ALLE Prompts zu generieren (viel schneller!)
            segments_text_structured = ""
            for idx, seg in enumerate(segments):
                segments_text_structured += f"Segment {idx+1} [{seg['start']}-{seg['end']}s]: {seg['text'].strip()}\n"

            prompt_request = f"""You are a cinematic director. Generate {len(segments)} distinct, hyper-detailed visual prompts in English for a cinematic dark motivational faceless video. 
Output ONLY {len(segments)} numbered prompts, separated by newlines. No intro, no explanations. Make each prompt match the text and feeling of its corresponding segment below perfectly.
Transcript Segments:
"{segments_text_structured}"
"""
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_request}],
                model="llama-3.3-70b-versatile",
            )
            
            raw_prompts_raw = chat_completion.choices[0].message.content.strip().split("\n")
            # Prompts säubern
            prompts_final = [p.strip("- ").strip("1234567890. ") for p in raw_prompts_raw if p.strip()][:len(segments)]
            
            # 3. KI-BILDER GENERIEREN (Pollinations)
            st.info("🎨 KI generiert vertikale Fullscreen-Bilder...")
            for idx, p_text in enumerate(prompts_final):
                encoded_p = urllib.parse.quote(p_text)
                # Volle 1080x1920 Vertikalauflösung, dunkle Cinematic-Ästhetik
                img_url = f"https://image.pollinations.ai/prompt/{encoded_p}%20cinematic%20dark%20moody%20faceless%20aesthetic%20vertical%209:16?width=1080&height=1920&nologo=true&seed={idx+75}"
                
                img_bytes = requests.get(img_url).content
                img_filename = f"ai_img_{idx}.png"
                with open(img_filename, "wb") as img_file:
                    img_file.write(img_bytes)
                image_paths.append(img_filename)
                
                # Exakte Dauer aus Whisper-Segmenten
                seg_duration = segments[idx]["end"] - segments[idx]["start"]
                segment_durations.append(seg_duration)

            # 4. VIDEOSCHNITT (MoviePy & Ken-Burns-Vollbild)
            st.info("🎬 Animiere Vollbild-Bilder & synchronisiere Video... (Bitte Warten!)")
            audio_full = AudioFileClip(temp_audio_path)
            
            video_clips = []
            for idx, img_p in enumerate(image_paths):
                # Dauer des spezifischen Segments
                current_duration = segment_durations[idx]
                # VOLLBILD-GARANTIE: Skalieren auf 1080x1920 (9:16 Vertical)
                img_clip = ImageClip(img_p).resize(newsize=(1080, 1920)).set_duration(current_duration)
                
                # Zoom-Animation von 1.0 auf 1.15
                zoomed = img_clip.fx(vfx.resize, lambda t: 1 + 0.15 * (t / current_duration))
                comp = CompositeVideoClip([zoomed.set_position('center')], size=(1080, 1920)).set_duration(current_duration)
                video_clips.append(comp)
                
            # Alle Clips verbinden
            final_bg = concatenate_videoclips(video_clips, method="compose").set_audio(audio_full)
            
            # 5. TEXT-OVERLAY (PATCH: Keine schwarze Leiste!)
            st.info("🖌️ Erstelle transparentes Text-Overlay...")
            text_img_path = "text_overlay.png"
            # Volle Transparenz (Dunkler Hintergrund weggelassen)
            img_overlay = Image.new('RGBA', (800, 200), color=(0, 0, 0, 0)) 
            draw = ImageDraw.Draw(img_overlay)
            # Nutze Standard-Font, falls kein Font hochgeladen ist. Outline-Trick für Lesbarkeit.
            # Weißer Text, schwarze Outline.
            draw.text((100, 70), "🔊 Sound On | Deep Mindset", fill="white", stroke_fill="black", stroke_width=4)
            img_overlay.save(text_img_path)
            
            txt_clip = ImageClip(text_img_path).set_position(('center', 1500)).set_duration(audio_full.duration)
            
            final_video = CompositeVideoClip([final_bg, txt_clip])
            output_path = "final_faceless_improved.mp4"
            
            # 6. TURBO-RENDERING FÜR DIE CLOUD
            # FPS auf 15 reduziert (für TikTok völlig ok, spart 40% Renderzeit), preset ultrafast
            final_video.write_videofile(
                output_path, 
                fps=15, 
                codec="libx264", 
                audio_codec="aac",
                preset="ultrafast", 
                threads=4,          
                logger=None         
            )
            
            # Video im Gedächtnis speichern
            st.session_state.video_path = output_path
            st.session_state.video_ready = True
            
            st.success("🎉 Dein verbessertes, synchrones Faceless Video ist fertig!")

# --- DOWNLOAD BEREICH (Sicher vor App-Resets) ---
if st.session_state.video_ready and os.path.exists(st.session_state.video_path):
    st.markdown("### Dein Video ist bereit zum Download!")
    with open(st.session_state.video_path, "rb") as f:
        st.download_button(
            label="⬇️ Video auf iPhone speichern", 
            data=f, 
            file_name="faceless_video_improved.mp4", 
            mime="video/mp4"
        )
