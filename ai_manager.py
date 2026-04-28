import google.generativeai as genai
import streamlit as st

Wir holen den Key sicher aus den Streamlit-Einstellungen
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_spanish_tutor_response(user_input, known_words):
    # Wir nutzen das Modell 'gemini-1.5-flash'
    model = genai.GenerativeModel('gemini-1.5-flash')

    context = f"""
    Du bist ein Spanischlehrer. Der Nutzer kennt bereits diese Wörter: {known_words}.
    
Wenn der Nutzer einen Fehler macht, korrigiere ihn sanft.
Nutze Vokabeln, die leicht über dem bekannten Level liegen.
Antworte nur auf Spanisch, außer bei Erklärungen.
"""

# Hier passiert der Aufruf, der aktuell noch den Fehler wirft
response = model.generate_content(context + "\nNutzer: " + user_input)
return response.text
