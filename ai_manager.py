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
   unit = data["unit"]

   if mode == "Konversation":
       prompt = f"""Du bist ein Spanisch-Tutor. Nutzer ist in Unit {unit}.
       Bekannte Wörter: {words}. 
       ANTWORTE NUR AUF SPANISCH mit diesen Wörtern. Wenn er Fehler macht, erkläre sie kurz auf DEUTSCH und kehre zu Spanisch zurück."""
   else:
       prompt = f"""Du bist ein Duolingo-Lehrer. Unit {unit}. Bekannte Wörter: {words}.
       PFAD-LOGIK: 
       1. Wenn der Nutzer gerade eine Antwort gegeben hat, korrigiere ihn.
       2. Frage dann entweder ein altes Wort ab ODER führe ein neues Wort ein, das zu Unit {unit} passt.
       3. Halte es kurz und motivierend. Nutze Emojis."""

   res = client.chat.completions.create(
       messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
       model="llama-3.1-8b-instant"
   )
   return res.choices[0].message.content
