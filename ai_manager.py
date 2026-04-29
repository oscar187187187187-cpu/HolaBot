import os
import tempfile
import streamlit as st
from groq import Groq
from gtts import gTTS

def transcribe_audio(audio_bytes, lang_code):
   client = Groq(api_key=st.secrets["GROQ_API_KEY"])
   with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
       tmp.write(audio_bytes)
       tmp_path = tmp.name
   try:
       with open(tmp_path, "rb") as f:
           trans = client.audio.transcriptions.create(file=(tmp_path, f.read()), model="whisper-large-v3", language=lang_code)
       return trans.text
   finally: os.remove(tmp_path)

def text_to_speech(text):
   try:
       tts = gTTS(text=text, lang='es')
       tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
       tts.save(tmp.name)
       return tmp.name
   except: return None

def get_tutor_response(user_input, data, mode):
   client = Groq(api_key=st.secrets["GROQ_API_KEY"])
   words = data["known_words"]
   level = (data["xp"] // 100) + 1

   if mode == "Konversation":
       prompt = f"Tutor Modus. Level {level}. Vokabeln: {words}. Antworte auf Spanisch NUR mit diesen Wörtern. Erkläre Fehler auf Deutsch."
   else:
       # Lernpfad Logik: KI entscheidet zwischen Wiederholung oder Neuem
       prompt = f"""Lernpfad Modus. Level {level}. Bekannte Wörter: {words}.
       Entscheide:
       1. Wenn der Nutzer weniger als 10 Wörter kennt, bringe 1 neues Wort bei.
       2. Wenn er mehr kennt, frage ein zufälliges altes Wort aus der Liste ab (Übersetzung Spanisch-Deutsch).
       Gib dem Nutzer eine XP Belohnung in Aussicht. Antworte motivierend wie Duolingo."""

   res = client.chat.completions.create(
       messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
       model="llama-3.1-8b-instant"
   )
   return res.choices[0].message.content
