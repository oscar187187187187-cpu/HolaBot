import os
import tempfile
import streamlit as st
from groq import Groq
from gtts import gTTS

def transcribe_audio(audio_bytes, lang_code):
    """Übersetzt Sprache zu Text (mit Sprach-Auswahl de/es)."""
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            trans = client.audio.transcriptions.create(
                file=(tmp_path, f.read()), 
                model="whisper-large-v3", 
                language=lang_code
            )
        return trans.text
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def text_to_speech(text):
    """Generiert die spanische Stimme."""
    try:
        tts = gTTS(text=text, lang='es')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return tmp.name
    except: 
        return None

def get_smart_response(user_input, mode, data_context, chat_history):
    """Die Haupt-KI-Logik für beide Modi."""
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    if mode == "Konversation":
        known_words = data_context.get("vocab", [])
        prompt = f"""Du bist ein strenger Spanisch-Partner. 
        REGEL 1: Du darfst für deine spanischen Sätze AUSSCHLIESSLICH diese Vokabeln benutzen: {known_words}. 
        REGEL 2: Wenn der Schüler einen Fehler macht, korrigiere ihn ZUERST AUF DEUTSCH, erkläre es kurz, und antworte dann auf Spanisch (nur mit bekannten Wörtern)."""
    else:
        # Lernpfad-Modus
        lesson_type = data_context["lesson_type"]
        unit_words = data_context["unit_words"]
        
        prompts = {
            "NEU LERNEN 1": f"Bringe diese neuen Wörter bei: {unit_words}. Erkläre die Bedeutung auf Deutsch und bilde einen einfachen Beispielsatz.",
            "NEU LERNEN 2": f"Vertiefe diese Wörter: {unit_words}. Lass den Nutzer einen Satz damit bilden.",
            "WIEDERHOLUNG": f"Prüfung! Frage den Nutzer nach der deutschen ODER spanischen Übersetzung dieser Wörter: {unit_words}.",
            "HÖREN": f"Antworte NUR auf Spanisch mit diesen Wörtern: {unit_words}. Der Nutzer soll versuchen zu antworten.",
            "MASTER-TEST": f"Finaler Test der Unit! Stelle eine knackige Aufgabe zu diesen Wörtern: {unit_words}."
        }
        prompt = prompts.get(lesson_type, prompts["NEU LERNEN 1"])

    res = client.chat.completions.create(
        messages=[{"role": "system", "content": prompt}, *chat_history[-4:], {"role": "user", "content": user_input}],
        model="llama-3.1-70b-versatile"
    )
    return res.choices[0].message.content
