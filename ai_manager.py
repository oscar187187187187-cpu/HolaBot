import google.generativeai as genai
import os

# API Key hier einfügen oder als Umgebungsvariable
os.environ["GOOGLE_API_KEY"] = "DEIN_API_KEY_HIER"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def get_spanish_tutor_response(user_input, known_words):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    context = f"""
    Du bist ein Spanischlehrer. Der Nutzer kennt bereits diese Wörter: {known_words}.
    - Wenn der Nutzer einen Fehler macht, korrigiere ihn sanft.
    - Nutze Vokabeln, die leicht über dem bekannten Level liegen.
    - Antworte nur auf Spanisch, außer bei Erklärungen.
    """
    
    response = model.generate_content(context + "\nNutzer: " + user_input)
    return response.text