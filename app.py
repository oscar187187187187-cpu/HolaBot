import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import base64
import speech_recognition as sr
import re

# --- EINSTELLUNGEN ---
st.set_page_config(page_title="Spanisch Video-Call (Groq)", page_icon="🇪🇸", layout="centered")

# API-Key aus den Streamlit Secrets laden (Für GROQ)
try:
    # Wir nennen es GROQ_API_KEY, passend zum Anbieter
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
except KeyError:
    st.error("🚨 Key fehlt! Geh in die Streamlit Settings -> Secrets und füge GROQ_API_KEY = 'gsk_...' hinzu.")
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
def get_groq_response(system_prompt, user_text=None):
    """Holt die Antwort über die offizielle Groq-Bibliothek."""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(st.session_state.history)
    
    if user_text:
        messages.append({"role": "user", "content": user_text})
        
    try:
        # Wir nutzen llama3-8b, das ist extrem schnell und perfekt für Groq
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.1 # Sehr niedrig für maximale Regeltreue
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Lo siento, error de Groq: {str(e)}"

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
st.title("🇪🇸 Spanisch Video-Call (Groq)")

# 1. SETUP-BILDSCHIRM
if not st.session_state.call_started:
    st.write("### 📝 Vorbereitung")
    st.write("Füge hier deine Wörter ein. Die Groq-KI wird nur diese nutzen.")
    
    vocab_input = st.text_area("Deine Vokabeln (kommagetrennt oder mit Leerzeichen):", height=150)
    
    if st.button("📞 Video-Call starten", use_container_width=True):
        words = [w.strip().lower() for w in re.split(r'[,\s\n]+', vocab_input) if w.strip()]
        
        if len(words) < 5:
            st.warning("Bitte füge ein paar Wörter hinzu.")
        else:
            st.session_state.vocab_list = words
            st.session_state.call_started = True
            
            # Erste Nachricht generieren
            all_words_str = ", ".join(words)
            sys_prompt = f"Du bist ein spanischer Sprachpartner. WICHTIGSTE REGEL: Du darfst für deine Antworten AUSSCHLIESSLICH Wörter aus dieser Liste verwenden: [{all_words_str}]. Keine anderen Wörter! Stelle mir jetzt sofort die erste kurze Frage auf Spanisch."
            
            with st.spinner("Verbindung über Groq wird hergestellt..."):
                ai_reply = get_groq_response(sys_prompt, "Start")
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                text_to_speech(ai_reply)
            st.rerun()

# 2. CALL-BILDSCHIRM
if st.session_state.call_started:
    st.markdown("""
        <div style="background-color: #1E1E1E; border-radius: 20px; padding: 40px; text-align: center; margin-bottom: 20px;">
            <h1 style='font-size: 120px; margin: 0;'>👤</h1>
            <p style="color: #4CAF50; margin-top: 10px;">Groq Video-Call Aktiv</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_to_play:
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{st.session_state.audio_to_play}" type="audio/mp3"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)
        st.session_state.audio_to_play = None 
        
    with st.expander("Transkript anzeigen"):
        for msg in st.session_state.history:
            role = "Du" if msg["role"] == "user" else "KI"
            st.markdown(f"**{role}:** {msg['content']}")
            
    st.write("---")
    
    st.write("### 🎙️ Du bist dran")
    audio_value = st.audio_input("Halte den Knopf zum Sprechen:")
    
    if audio_value:
        with st.spinner("Groq antwortet extrem schnell..."):
            user_text = transcribe_audio(audio_value.getvalue())
            
            if user_text:
                st.session_state.history.append({"role": "user", "content": user_text})
                
                all_words_str = ", ".join(st.session_state.vocab_list)
                sys_prompt = f"Du bist ein spanischer Sprachpartner. REGEL: Du darfst AUSSCHLIESSLICH diese Wörter verwenden: [{all_words_str}]. Keine anderen. Reagiere kurz und stelle eine neue Frage."
                
                ai_reply = get_groq_response(sys_prompt)
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                text_to_speech(ai_reply)
                st.rerun()
            else:
                st.error("Nicht verstanden. Bitte noch einmal sprechen.")
                
    if st.button("Call beenden", type="primary"):
        st.session_state.call_started = False
        st.session_state.history = []
        st.rerun()
