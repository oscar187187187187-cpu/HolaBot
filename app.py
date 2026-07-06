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
st.set_page_config(page_title="Spanisch Video-Call (Groq)", page_icon="🇪🇸", layout="centered")

# API-Key aus den Streamlit Secrets laden
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
except KeyError:
    st.error("🚨 Key fehlt! Geh in die Streamlit Settings -> Secrets und füge GROQ_API_KEY = 'gsk_...' hinzu.")
    st.stop()

# --- DATEN-SPEICHER FUNKTIONEN (STREAK, VOKABELN, CHAT) ---
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
        return data["streak"] 
    elif data["last_date"] == yesterday:
        data["streak"] += 1   
    else:
        data["streak"] = 1    
        
    data["last_date"] = today
    save_streak(data)
    return data["streak"]

# FUNKTION 1: Vokabeln dauerhaft speichern & laden
def load_saved_vocab():
    if os.path.exists("saved_vocab.json"):
        try:
            with open("saved_vocab.json", "r", encoding="utf-8") as f:
                return json.load(f).get("vocab", "")
        except:
            pass
    return ""

def save_vocab(vocab_string):
    with open("saved_vocab.json", "w", encoding="utf-8") as f:
        json.dump({"vocab": vocab_string}, f, ensure_ascii=False)

# FUNKTION 2: Laufenden Chat sichern & wiederherstellen
def save_active_call():
    data = {
        "history": st.session_state.history,
        "vocab_list": st.session_state.vocab_list
    }
    with open("active_call.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def load_active_call():
    if os.path.exists("active_call.json"):
        try:
            with open("active_call.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

def delete_active_call():
    if os.path.exists("active_call.json"):
        try:
            os.remove("active_call.json")
        except:
            pass

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
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

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
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in st.session_state.history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    if user_text:
        messages.append({"role": "user", "content": user_text})
        
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.1, 
            max_tokens=60
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Lo siento, error de Groq: {str(e)}"

def text_to_speech(text):
    # ANTI-FREEZE SICHERHEIT: Falls Google streikt, bricht es hier ab und die App läuft weiter!
    try:
        tts = gTTS(text, lang='es')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        st.session_state.audio_to_play = b64
    except Exception as e:
        st.error("Audio konnte nicht geladen werden (Google-Timeout). Bitte lies den Text der KI unten!")
        st.session_state.audio_to_play = None

def transcribe_audio_groq(audio_bytes):
    # STABILE SPRACHERKENNUNG: Nutzt jetzt Groq Whisper anstelle von Google
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            language="es"
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
    st.write("Deine Vokabeln sind dauerhaft gespeichert. Drücke einfach auf Start oder setze den alten Call fort!")
    
    saved_vocab_data = load_saved_vocab()
    vocab_input = st.text_area("Deine Vokabeln (kommagetrennt oder mit Leerzeichen):", value=saved_vocab_data, height=150)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📞 Neuer Video-Call", use_container_width=True, type="primary"):
            words = [w.strip().lower() for w in re.split(r'[,\s\n]+', vocab_input) if w.strip()]
            
            if len(words) < 2:
                st.warning("Bitte füge deine Wörter ein.")
            else:
                st.session_state.vocab_list = words
                st.session_state.call_started = True
                st.session_state.last_processed_audio = None
                save_vocab(vocab_input) 
                
                all_words_str = ", ".join(words)
                sys_prompt = (
                    f"MANDATORY LOCKDOWN RULE: You are a Spanish conversation partner. "
                    f"ULTRA-STRICT RULE 1: You can ONLY and EXCLUSIVELY use the words from this exact list: [{all_words_str}]. "
                    f"It is strictly FORBIDDEN to use any other Spanish word outside of this list, not even common words like 'bien', 'que', 'haces' UNLESS they are explicitly written in the list! If a word is not listed, you cannot use it. "
                    f"RULE 2: Speak exactly ONE short sentence and ask exactly ONE question. "
                    f"RULE 3: Do not generate alternatives, lists, or comments. Stop instantly."
                )
                
                with st.spinner("Verbindung wird aufgebaut..."):
                    ai_reply = get_groq_response(sys_prompt, "Start")
                    st.session_state.history.append({"role": "assistant", "content": ai_reply})
                    save_active_call() 
                    text_to_speech(ai_reply)
                st.rerun()

    with col2:
        saved_call = load_active_call()
        if saved_call:
            if st.button("🔄 Letzten Call fortsetzen", use_container_width=True):
                st.session_state.history = saved_call["history"]
                st.session_state.vocab_list = saved_call["vocab_list"]
                st.session_state.call_started = True
                st.session_state.last_processed_audio = None
                st.rerun()
        else:
            st.button("🔄 Kein aktiver Call offen", use_container_width=True, disabled=True)

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
            <small style="color: #888;">Du kannst das Fenster jederzeit schließen. Der Chat wird automatisch gespeichert!</small>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_to_play:
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{st.session_state.audio_to_play}" type="audio/mp3"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)
        st.session_state.audio_to_play = None 
        
    with st.expander("Transkript anzeigen"):
        for msg in st.session_state.history:
            role = "Du" if msg["role"] == "user" else "Groq KI"
            st.markdown(f"**{role}:** {msg['content']}")
            
    st.write("---")
    st.write("### 🎙️ Du bist dran")
    audio_value = st.audio_input("Halte den Knopf zum Sprechen:")
    
    if audio_value:
        current_audio_bytes = audio_value.getvalue()
        
        if st.session_state.last_processed_audio != current_audio_bytes:
            st.session_state.last_processed_audio = current_audio_bytes
            
            with st.spinner("Groq hört zu und überlegt..."):
                user_text = transcribe_audio_groq(current_audio_bytes)
                
                if user_text:
                    st.session_state.history.append({"role": "user", "content": user_text})
                    save_active_call() 
                    
                    all_words_str = ", ".join(st.session_state.vocab_list)
                    sys_prompt = (
                        f"MANDATORY LOCKDOWN RULE: You are a Spanish conversation partner. "
                        f"ULTRA-STRICT RULE 1: You can ONLY and EXCLUSIVELY use the words from this exact list: [{all_words_str}]. "
                        f"It is strictly FORBIDDEN to use any other Spanish word outside of this list! "
                        f"RULE 2: Speak exactly ONE short sentence and ask exactly ONE question. "
                        f"RULE 3: Do not generate alternatives or lists. Stop instantly. WRITE ONLY THE SPANISH SENTENCE YOU WILL SPEAK."
                    )
                    
                    ai_reply = get_groq_response(sys_prompt)
                    st.session_state.history.append({"role": "assistant", "content": ai_reply})
                    save_active_call() 
                    text_to_speech(ai_reply)
                    st.rerun()
                else:
                    st.error("Ich habe kein Audio erkannt. Bitte sprich noch einmal.")
                
    if st.button("Call komplett beenden & archivieren", type="primary"):
        if st.session_state.history:
            st.session_state.past_calls.append(st.session_state.history.copy())
        
        update_streak()
        delete_active_call() 
        st.session_state.call_started = False
        st.session_state.history = []
        st.session_state.last_processed_audio = None
        st.rerun()
