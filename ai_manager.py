import os
import streamlit as st
from groq import Groq

def get_spanish_tutor_response(user_input, known_words_dict):
   # API Key aus den Secrets holen
   api_key = st.secrets.get("GROQ_API_KEY")
   if not api_key:
       return "Fehler: Bitte hinterlege GROQ_API_KEY in den Streamlit Secrets."

   try:
       client = Groq(api_key=api_key)
       known_words = known_words_dict.get("known_words", [])

       system_prompt = f"""Du bist ein freundlicher Spanischlehrer. Der Schüler kennt diese Wörter: {known_words}.
       Korrigiere Fehler sanft auf Deutsch. Antworte auf Spanisch."""

       chat_completion = client.chat.completions.create(
           messages=[
               {"role": "system", "content": system_prompt},
               {"role": "user", "content": user_input}
           ],
           model="llama3-8b-8192", # Das ist ein extrem schnelles und kostenloses Modell
       )

       return chat_completion.choices[0].message.content
   except Exception as e:
       return f"KI-Fehler (Groq): {str(e)}"
