import streamlit as st
from groq import Groq
from gtts import gTTS
import tempfile

def get_lesson_response(user_input, lesson_type, unit_words, history):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    prompts = {
        "INTRO": f"Bringe dem Nutzer diese neuen spanischen Wörter bei: {unit_words}. Erkläre die Bedeutung kurz auf Deutsch und gib ein Beispiel.",
        "REVIEW": f"Wiederholung! Frage den Nutzer nach der Übersetzung dieser Wörter: {unit_words}. Korrigiere ihn streng aber motivierend.",
        "LISTENING": f"Hörverstehen! Antworte NUR auf Spanisch mit diesen Wörtern: {unit_words}. Der Nutzer soll versuchen zu verstehen.",
        "CONV": "Du bist ein lockerer Gesprächspartner. Antworte auf Spanisch. KEIN XP-MODUS."
    }
    
    prompt = prompts.get(lesson_type, prompts["INTRO"])
    
    res = client.chat.completions.create(
        messages=[{"role": "system", "content": prompt}, *history, {"role": "user", "content": user_input}],
        model="llama-3.1-70b-versatile" # Stärkeres Modell für bessere Logik
    )
    return res.choices[0].message.content

def text_to_speech(text):
    tts = gTTS(text=text, lang='es')
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name
