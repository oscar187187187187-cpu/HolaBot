import os
import tempfile
import json
import streamlit as st
from groq import Groq
from gtts import gTTS

def text_to_speech(text, lang='es'):
    """Wandelt Text in eine temporäre Audiodatei um (Audio-Übungen)."""
    try:
        tts = gTTS(text=text, lang=lang)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return tmp.name
    except Exception as e:
        return None

def transcribe_audio(audio_bytes, lang_code="es"):
    """Nutzt Whisper, um die Aussprache des Nutzers zu transkribieren."""
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
    except Exception:
        return None

def generate_lesson_exercise(unit, lesson, known_words):
    """
    Generiert dynamisch eine Duolingo-artige Übung.
    Gibt ein strukturiertes Dictionary zurück.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    prompt = f"""
    Du bist die Engine für eine Sprachlern-App. Der Nutzer ist in Unit {unit}, Lektion {lesson}.
    Bekannte Wörter: {known_words}.
    Erstelle EINE kleine Spanisch-Übung. Antworte AUSSCHLIESSLICH in validem JSON-Format.
    Mögliche Typen: "translation" (Spanisch zu Deutsch) oder "fill_in_the_blank".
    
    Beispiel JSON:
    {{
      "type": "translation",
      "question": "Wie sagt man 'Hallo' auf Spanisch?",
      "spanish_text": "Hola",
      "correct_answer": "Hola",
      "hint": "Startet mit H"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        # Extrahiere JSON aus der Antwort
        content = response.choices[0].message.content
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        json_str = content[start_idx:end_idx]
        
        return json.loads(json_str)
    except Exception:
        # Fallback, falls die KI kein sauberes JSON liefert oder API ausfällt
        return {
            "type": "translation",
            "question": "Übersetze auf Spanisch: 'Danke'",
            "spanish_text": "Gracias",
            "correct_answer": "Gracias",
            "hint": "G..."
        }
