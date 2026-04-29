import google.generativeai as genai
import streamlit as st

# Holt den Key sicher aus der Streamlit Cloud
if "GOOGLE_API_KEY" in st.secrets:
   genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_spanish_tutor_response(user_input, known_words_dict):
   try:
       model = genai.GenerativeModel('gemini-1.5-flash')
       known_words = known_words_dict.get("known_words", [])

       # Die verbesserte Anweisung an die KI (Bonus Feature)
       system_prompt = f"""Du bist ein freundlicher, muttersprachlicher Spanischlehrer namens HolaBot.
       Dein Schüler kennt bisher ungefähr diese Vokabeln: {known_words}.
       Deine Regeln:
       1. Antworte primär auf Spanisch, aber halte es auf einem anfängerfreundlichen Niveau.
       2. Wenn der Schüler einen Fehler macht, korrigiere ihn sanft auf Deutsch.
       3. Nutze ab und zu ein neues Wort und erkläre es kurz.
       4. Halte deine Antworten kurz, natürlich und motivierend."""

       # Fügt die Systemanweisung und die Nutzernachricht zusammen
       full_prompt = f"{system_prompt}\n\nSchüler: {user_input}\nHolaBot:"

       response = model.generate_content(full_prompt)
       return response.text
   except Exception as e:
       return f"Ups, es gab ein Problem mit der KI-Verbindung. Fehlermeldung: {e}"
