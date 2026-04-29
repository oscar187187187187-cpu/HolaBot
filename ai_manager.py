import os
import tempfile
import streamlit as st
from groq import Groq
from gtts import gTTS

# Sprach-zu-Text (Dein Mikrofon)
def transcribe_audio(audio_bytes):
   api_key = st.secrets.get("GROQ_API_KEY")
   if not api_key: return "API-Key fehlt."
   client = Groq(api_key=api_key)

   with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
       temp_audio.write(audio_bytes)
       temp_audio_path = temp_audio.name

   try:
       with open(temp_audio_path, "rb") as file:
           transcription = client.audio.transcriptions.create(
             file=(temp_audio_path, file.read()),
             model="whisper-large-v3",
           )
       os.remove(temp_audio_path)
       return transcription.text
   except Exception as e:
       return f"Audio-Fehler: {str(e)}"

# Text-zu-Sprache (Die KI spricht)
def text_to_speech(text):
   try:
       # Wir stellen es auf Spanisch. Hinweis: Deutsche Erklärungen klingen dann lustig mit spanischem Akzent!
       tts = gTTS(text=text, lang='es', slow=False)
       temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
       tts.save(temp_file.name)
       return temp_file.name
   except Exception:
       return None

# Chat-KI (Deine Modi)
def get_spanish_tutor_response(user_input, known_words_dict, mode):
   api_key = st.secrets.get("GROQ_API_KEY")
   client = Groq(api_key=api_key)
   known_words = known_words_dict.get("known_words", [])

   if mode == "Konversation":
       system_prompt = f"""Du bist ein strenger, aber freundlicher Spanischlehrer.
       REGEL 1: Du darfst für deine spanischen Antworten AUSSCHLIESSLICH diese Vokabeln benutzen: {known_words}. Wenn du damit keinen Satz bilden kannst, sag auf Deutsch: 'Dein Wortschatz ist noch zu klein dafür. Bitte nutze den Lernmodus.'
       REGEL 2: Wenn der Schüler einen Grammatik- oder Vokabelfehler macht, weise ihn zuerst auf Deutsch darauf hin, erkläre kurz wie es richtig heißt, und antworte dann auf Spanisch (nur mit bekannten Wörtern!)."""
   else:
       system_prompt = f"""Du bist im Lernmodus. Der Schüler kennt diese Wörter: {known_words}.
       Bringe dem Schüler basierend auf seiner Eingabe 2 NEUE, nützliche spanische Wörter bei.
       Erkläre sie auf Deutsch, gib ein Beispiel und bitte den Schüler, einen Satz damit zu bilden."""

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
