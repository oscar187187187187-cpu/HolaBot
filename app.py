import streamlit as st
import requests
from gtts import gTTS
import io
import base64
import speech_recognition as sr
import re

# --- EINSTELLUNGEN ---
st.set_page_config(page_title="Spanisch Video-Call", page_icon="🇪🇸", layout="centered")

# API-Key aus den Streamlit Secrets laden
try:
    API_KEY = st.secrets["XAI_API_KEY"]
except KeyError:
    st.error("🚨 Bitte trage deinen API-Key in den Streamlit Secrets ein (Name: XAI_API_KEY).")
    st.stop()

# --- SPEICHER INITIALISIEREN ---
if "history" not in st.session_state:
    st.session_state.history = []
if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = []
if "call_started" not in st.session_state:
    st.session_state.call_started = False
if "audio_to_play" not in st.session_state:
    st.session_state.audio_to_play = None

# --- FUNKTIONEN ---
def get_ai_response(system_prompt, user_text=None):
    """Sendet die Nachrichten an Grok (xAI) und holt die Antwort."""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(st.session_state.history)
    
    if user_text:
        messages.append({"role": "user", "content": user_text})
        
    data = {
        "model": "grok-beta",
        "messages": messages,
        "temperature": 0.1 # Sehr niedrig, damit die KI keine anderen Wörter erfindet
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return "Lo siento, error."

def text_to_speech(text):
    """Wandelt den Text der KI in eine spanische Sprachnachricht um."""
    tts = gTTS(text, lang='es')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    b64 = base64.b64encode(fp.getvalue()).decode()
    st.session_state.audio_to_play = b64

def transcribe_audio(audio_bytes):
    """Wandelt deine Sprachaufnahme in Text um."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data, language="es-ES")
        except:
            return None

# --- APP LAYOUT ---
st.title("🇪🇸 Spanisch Video-Call")

# 1. SETUP-BILDSCHIRM (Wörter einfügen)
if not st.session_state.call_started:
    st.write("### 📝 Vorbereitung")
    st.write("Füge hier alle Wörter ein, die die KI benutzen darf. Sie wird mit nichts anderem antworten.")
    
    vocab_input = st.text_area("Deine Vokabeln (kommagetrennt oder mit Leerzeichen):", height=150)
    
    if st.button("📞 Video-Call starten", use_container_width=True):
        # Bereinigt die Eingabe und filtert leere Wörter heraus
        words = [w.strip().lower() for w in re.split(r'[,\s\n]+', vocab_input) if w.strip()]
        
        if len(words) < 5:
            st.warning("Bitte füge mindestens ein paar Wörter ein (z.B. Pronomen, Verben und Nomen).")
        else:
            st.session_state.vocab_list = words
            st.session_state.call_started = True
            
            # Erste Nachricht der KI generieren
            all_words_str = ", ".join(words)
            sys_prompt = f"Du bist ein spanischer Sprachpartner. WICHTIGSTE REGEL: Du darfst für deine Antworten AUSSCHLIESSLICH Wörter aus dieser Liste verwenden: [{all_words_str}]. Keine anderen Wörter! Stelle mir jetzt sofort die erste kurze Frage auf Spanisch."
            
            with st.spinner("Verbindung wird hergestellt..."):
                ai_reply = get_ai_response(sys_prompt, "Start")
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                text_to_speech(ai_reply)
            st.rerun()

# 2. CALL-BILDSCHIRM (Nur Sprache)
if st.session_state.call_started:
    # Simulierter Video-Call Avatar
    st.markdown("""
        <div style="background-color: #1E1E1E; border-radius: 20px; padding: 40px; text-align: center; margin-bottom: 20px;">
            <h1 style='font-size: 120px; margin: 0;'>👤</h1>
            <p style="color: #4CAF50; margin-top: 10px;">Verbunden</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Audio der KI automatisch abspielen
    if st.session_state.audio_to_play:
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{st.session_state.audio_to_play}" type="audio/mp3"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)
        st.session_state.audio_to_play = None 
        
    # Transkription des Gesprächs anzeigen (damit du siehst, was verstanden wurde)
    with st.expander("Transkript der Konversation anzeigen"):
        for msg in st.session_state.history:
            if msg["role"] == "user":
                st.markdown(f"**Du:** {msg['content']}")
            else:
                st.markdown(f"**KI:** {msg['content']}")
            
    st.write("---")
    
    # AUSSCHLIESSLICH MIKROFON-EINGABE (Kein Textfeld)
    st.write("### 🎙️ Du bist dran")
    audio_value = st.audio_input("Halte den Knopf zum Sprechen auf Spanisch:")
    
    if audio_value:
        with st.spinner("KI überlegt..."):
            user_text = transcribe_audio(audio_value.getvalue())
            
            if user_text:
                st.session_state.history.append({"role": "user", "content": user_text})
                
                # KI antwortet streng mit deinen Wörtern
                all_words_str = ", ".join(st.session_state.vocab_list)
                sys_prompt = f"Du bist ein spanischer Sprachpartner. REGEL: Du darfst AUSSCHLIESSLICH diese Wörter verwenden: [{all_words_str}]. Keine anderen. Reagiere auf das, was der User sagt, und stelle eine neue kurze Frage aus deinen erlaubten Wörtern."
                
                ai_reply = get_ai_response(sys_prompt)
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                text_to_speech(ai_reply)
                
                st.rerun()
            else:
                st.error("Ich konnte dich nicht verstehen. Bitte sprich nochmal.")
                
    if st.button("Call beenden", type="primary"):
        st.session_state.call_started = False
        st.session_state.history = []
        st.rerun()
