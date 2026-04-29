mport google.generativeai as genai
import streamlit as st

if "GOOGLE_API_KEY" in st.secrets:
   genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_spanish_tutor_response(user_input, known_words):
   model = genai.GenerativeModel('gemini-1.5-flash')
   context = f"Du bist ein Spanischlehrer. Der Nutzer kennt diese Wörter: {known_words}. Korrigiere Fehler sanft. Nutze Vokabeln leicht über seinem Level. Antworte nur auf Spanisch, außer bei Erklärungen."
   response = model.generate_content(context + "\nNutzer: " + user_input)
   return response.text
