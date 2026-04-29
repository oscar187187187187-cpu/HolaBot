import os
import tempfile
import streamlit as st
from groq import Groq
from gtts import gTTS

def transcribe_audio(audio_bytes, language_code):
   api_key = st.secrets.get("GROQ_API_KEY")
   if not api_key: return "API-Key fehlt."
   client = Groq(api_key=api_key)

   with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
       temp_audio.write(audio_bytes)
       temp_audio_path = temp_audio.name

   try:
       with open(temp_audio_path, "rb") as file:
           # Hier erzwingen wir die Sprache, damit die KI nicht auf Englisch halluziniert
           transcription = client.audio.transcriptions.create(
             file=(temp_audio_path, file.read()),
             model="whisper-large-v3",
             language=language_code
           )
       os.remove(temp_audio_path)
       return transcription.text
   except Exception as e:
       return f"Audio-Fehler: {str(e)}"

def text_to_speech(text):
   try:
       tts = gTTS(text=text, lang='es', slow=False)
       temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
       tts.save(temp_file.name)
       return temp_file.name
   except Exception:
       return None

def get_spanish_tutor_response(user_input, known_words_dict, mode, level):
   api_key = st.secrets.get("GROQ_API_KEY")
   client = Groq(api_key=api_key)
   known_words = known_words_dict.get("known_words", [])

   if mode == "Konversation":
       system_prompt = f"""Du bist ein strenger Spanischlehrer. Der Nutzer ist auf Level {level}.
       REGEL 1: Du darfst für deine spanischen Sätze AUSSCHLIESSLICH diese Vokabeln benutzen: {known_words}. Wenn sein Wortschatz für eine sinnvolle Antwort nicht reicht, sag auf Deutsch: 'Dein Wortschatz (Level {level}) reicht dafür noch nicht. Bitte wechsle in den Lernmodus.'
       REGEL 2: Wenn der Schüler einen Fehler macht, korrigiere ihn zuerst auf Deutsch, erkläre warum, und antworte dann auf Spanisch (nur mit bekannten Wörtern)."""
   else:
       system_prompt = f"""Du bist ein Spanischlehrer im Duolingo-Stil. Der Nutzer ist auf Level {level}.
       Er kennt diese Vokabeln: {known_words}.
       DEINE AUFGABE: Bringe dem Schüler passend zu Level {level} exakt 2 NEUE Wörter bei.
       Erkläre sie auf Deutsch. Bilde dann einen Beispielsatz, der AUSSCHLIESSLICH aus seinen bereits bekannten Wörtern PLUS dem neuen Wort besteht.
       Fordere ihn auf, selbst etwas damit zu bilden."""

   try:
       chat_completion = client.chat.completions.create(
           messages=[
               {"role": "system", "content": system_prompt},
               {"role": "user", "content": user_input}
           ],
           model="llama-3.1-8b-instant",
       )
       return chat_completion.choices[0].message.content
   except Exception as e:
       return f"KI-Fehler: {str(e)}"
