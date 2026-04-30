import os
import tempfile
import streamlit as st
from groq import Groq
from gtts import gTTS

def transcribe_audio(audio_bytes, lang_code):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(tmp_path, f.read()),
                model="whisper-large-v3",
                language=lang_code
            )
        os.remove(tmp_path)
        return transcription.text
    except Exception as e:
        return f"Fehler bei der Transkription: {str(e)}"

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='es')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return tmp.name
    except Exception:
        return None

def get_ai_response(user_input, mode, context_data, history):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    if mode == "Sandbox":
        # Wortschatz-Gefängnis Logik
        allowed = context_data.get("vocab", [])
        system_prompt = f"""Du bist ein Spanisch-Tutor im Sandbox-Modus. 
        REGEL 1: Du darfst NUR diese Wörter verwenden: {allowed}.
        REGEL 2: Wenn der Nutzer einen Fehler macht, korrigiere ihn auf DEUTSCH.
        REGEL 3: Antworte kurz und präzise."""
    else:
        # Lernpfad Logik
        lesson_type = context_data.get("type", "Übung")
        words = context_data.get("words", [])
        system_prompt = f"""Du bist ein motivierender Sprachlehrer. 
        Aktueller Fokus: {words}. Modus: {lesson_type}.
        Gib Feedback zu Fehlern auf Deutsch und fordere den Nutzer auf Spanisch heraus."""

    messages = [{"role": "system", "content": system_prompt}]
    # Kontext-Fenster begrenzen
    for h in history[-6:]:
        messages.append(h)
    messages.append({"role": "user", "content": user_input})

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7
    )
    return completion.choices[0].message.content
