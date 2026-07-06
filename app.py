import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import base64
import re
import os
import json
from datetime import datetime, timedelta

# --- EINSTELLUNGEN ---
st.set_page_config(page_title="Spanisch Video-Call (Groq Edition)", page_icon="🇪🇸", layout="centered")

# API-Key aus den Streamlit Secrets laden (Für GROQ)
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
except KeyError:
    st.error("🚨 Key fehlt! Geh in die Streamlit Settings -> Secrets und füge GROQ_API_KEY = 'gsk_...' hinzu.")
    st.stop()

# --- STREAK FUNKTIONEN ---
def load_streak():
    if os.path.exists("streak_data.json"):
        try:
            with open("streak_data.json", "r") as f:
                return json.load(f)
        except:
            pass
    return {"streak": 0, "last_date": None}

def save_streak(data):
    with open("streak_data.json", "w") as f:
        json.dump(data, f)

def update_streak():
    data = load_streak()
    today = datetime.now().date().isoformat()
    yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
    
    if data["last_date"] == today:
        return data["streak"]  # Heute schon gelernt
    elif data["last_date"] == yesterday:
        data["streak"] += 1   # Gestern gelernt, Streak geht hoch!
    else:
        data["streak"] = 1    # Tag verpasst, Neustart
        
    data["last_date"] = today
    save_streak(data)
    return data["streak"]

# --- SPEICHER INITIALISIEREN ---
if "history" not in st.session_state:
    st.session_state.history = []
if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = []
if "call_started" not in st.session_state:
    st.session_state.call_started = False
if "audio_to_play" not in st.session_state:
    st.session_state.audio_to_play = None
if "past_calls" not in st.session_state:
    st.session_state.past_calls = []

streak_info = load_streak()

# --- SIDEBAR DISPLAY ---
st.sidebar.title("📊 Dein Fortschritt")
st.sidebar.markdown(f"### 🔥 Streak: **{streak_info['streak']} Tage**")
if streak_info['last_date'] == datetime.now().date().isoformat():
    st.sidebar.success("✅ Heute schon gelernt!")
else:
    st.sidebar.warning("⚡ Heute noch nicht gelernt!")

# --- FUNKTIONEN FÜR KI & AUDIO ---
def get_groq_response(system_prompt, user_text=None):
    """Holt die Antwort über die offizielle Groq-Bibliothek mit dem Standard-Modell."""
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in st.session_state.history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    if user_text:
        messages.append({"role": "user", "content": user_text})
        
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.1
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

def transcribe_audio_groq(audio_bytes):
    """Wandelt deine Sprachaufnahme mit Groqs Whisper-large-v3-turbo in Text um."""
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            language="es" # Zwingt die KI, spanisch zu erkennen
        )
        return transcription.text
    except Exception as e:
        st.error(f"Fehler bei der Spracherkennung: {str(e)}")
        return None

# --- APP LAYOUT ---
st.title("🇪🇸 Spanisch Video-Call")

# 1. SETUP-BILDSCHIRM
if not st.session_state.call_started:
    st.write("### 📝 Vorbereitung")
    st.write("Füge hier deine 519 Wörter ein. Groq wird dich aktiv damit ausquetschen!")
    
    vocab_input = st.text_area("Deine Vokabeln (kommagetrennt oder mit Leerzeichen):", height=150)
    
    if st.button("📞 Video-Call starten", use_container_width=True):
        words = [w.strip().lower() for w in re.split(r'[,\s\n]+', vocab_input) if w.strip()]
        
        if len(words) < 5:
            st.warning("Bitte füge deine Wörter ein.")
        else:
            st.session_state.vocab_list = words
            st.session_state.call_started = True
            
            all_words_str = ", ".join(words)
            # NEUER PROMPT: Absolut strikt gegen extra Text!
            sys_prompt = (
                f"Du bist ein spanischer Sprachpartner. "
                f"REGEL 1: Du darfst für deine Antworten AUSSCHLIESSLICH Wörter aus dieser Liste verwenden: [{all_words_str}]. Keine anderen! "
                f"REGEL 2: Du führst das Gespräch aktiv und stellst eine kurze Frage auf Spanisch, um das Gespräch zu eröffnen. "
                f"REGEL 3 (EXTREM WICHTIG): Schreibe AUSSCHLIESSLICH den Text, den du auch aussprechen willst. Keine Erklärungen, keine Regieanweisungen, keine Kommentare wie 'Hier ist eine Frage:'. Nur der pure spanische Satz!"
            )
            
            with st.spinner("Verbindung zu Groq wird aufgebaut..."):
                ai_reply = get_groq_response(sys_prompt, "Start")
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                text_to_speech(ai_reply)
            st.rerun()

    if st.session_state.past_calls:
        st.write("---")
        with st.expander("📂 Gespeicherte alte Chats anzeigen", expanded=False):
            for i, past_chat in enumerate(reversed(st.session_state.past_calls)):
                st.markdown(f"##### 💾 Gespräch Durchlauf {len(st.session_state.past_calls) - i}")
                for msg in past_chat:
                    role = "Du" if msg["role"] == "user" else "Groq KI"
                    st.markdown(f"**{role}:** {msg['content']}")
                st.write("---")

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
        
    with st.expander("Transkript anzeigen (zum Nachlesen)"):
        for msg in st.session_state.history:
            role = "Du" if msg["role"] == "user" else "Groq KI"
            st.markdown(f"**{role}:** {msg['content']}")
            
    st.write("---")
    st.write("### 🎙️ Du bist dran")
    audio_value = st.audio_input("Halte den Knopf zum Sprechen:")
    
    if audio_value:
        with st.spinner("Groq Whisper übersetzt & KI antwortet..."):
            # Nutzt jetzt Groq Whisper für Sprache-zu-Text!
            user_text = transcribe_audio_groq(audio_value.getvalue())
            
            if user_text:
                st.session_state.history.append({"role": "user", "content": user_text})
                
                all_words_str = ", ".join(st.session_state.vocab_list)
                sys_prompt = (
                    f"Du bist ein spanischer Sprachpartner. REGEL 1: Du darfst AUSSCHLIESSLICH diese Wörter verwenden: [{all_words_str}]. "
                    f"REGEL 2: Du bist der Interviewer! Antworte extrem kurz (max 1 Satz) auf das, was der User sagt, und STELL SOFORT EINE NEUE FRAGE auf Spanisch. "
                    f"REGEL 3 (EXTREM WICHTIG): Schreibe AUSSCHLIESSLICH den Text, den du sagst. Keine Anmerkungen, keine Übersetzungen, keine Einleitungen. Nur der reine spanische Satz!"
                )
                
                ai_reply = get_groq_response(sys_prompt)
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                text_to_speech(ai_reply)
                st.rerun()
            else:
                st.error("Nicht verstanden. Bitte noch einmal sprechen.")
                
    if st.button("Call beenden (Streak sichern)", type="primary"):
        if st.session_state.history:
            st.session_state.past_calls.append(st.session_state.history.copy())
        
        update_streak()
        st.session_state.call_started = False
        st.session_state.history = []
        st.rerun()
