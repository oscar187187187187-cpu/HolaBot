import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import base64
import os
import json
import re
import random
from datetime import datetime, timedelta

# --- EINSTELLUNGEN ---
st.set_page_config(page_title="Spanisch Video-Call", page_icon="🇪🇸", layout="centered")

# API-Key aus den Streamlit Secrets laden
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    # ANTI-FREEZE UPDATE: max_retries=0 und timeout verhindern die unendliche Ladeschleife!
    client = Groq(api_key=GROQ_API_KEY, max_retries=0, timeout=15.0)
except KeyError:
    st.error("🚨 Key fehlt! Geh in die Streamlit Settings -> Secrets und füge GROQ_API_KEY = 'gsk_...' hinzu.")
    st.stop()

# --- DATEN-SPEICHER FUNKTIONEN ---
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

def load_past_calls():
    if os.path.exists("past_calls.json"):
        try:
            with open("past_calls.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []

def save_completed_call(history, vocab_list, difficulty):
    calls = load_past_calls()
    new_call = {
        "date": datetime.now().strftime("%d.%m.%Y - %H:%M"),
        "vocab_list": vocab_list,
        "history": history,
        "difficulty": difficulty
    }
    calls.append(new_call)
    with open("past_calls.json", "w", encoding="utf-8") as f:
        json.dump(calls, f, ensure_ascii=False)

def save_active_call():
    data = {
        "history": st.session_state.history,
        "vocab_list": st.session_state.vocab_list,
        "difficulty": st.session_state.difficulty 
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
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None
if "difficulty" not in st.session_state:
    st.session_state.difficulty = "🟡 Mittel"

streak_info = load_streak()
past_saved_calls = load_past_calls()

# --- SIDEBAR DISPLAY ---
st.sidebar.title("📊 Dein Fortschritt")
st.sidebar.markdown(f"### 🔥 Streak: **{streak_info['streak']} Tage**")
if streak_info['last_date'] == datetime.now().date().isoformat():
    st.sidebar.success("✅ Heute schon gelernt!")
else:
    st.sidebar.warning("⚡ Heute noch nicht gelernt!")

# --- FUNKTIONEN FÜR KI, AUDIO & LEHRER-FEEDBACK ---

def evaluate_spanish_sentence(user_text):
    """Prüft den Satz des Users auf Grammatik und Sinn (Der unsichtbare Lehrer)."""
    sys_prompt = (
        "Du bist ein strenger aber fairer Spanisch-Lehrer. Der User lernt Spanisch. "
        "Bewerte den folgenden Satz auf Grammatik, Wortwahl und Sinn. "
        "Antworte AUSSCHLIESSLICH im folgenden Format (ohne weitere Einleitungen):\n"
        "STUFE | FEEDBACK\n\n"
        "Für STUFE wähle exakt eines dieser drei Wörter: Perfekt, Fehler, Falsch.\n"
        "Für FEEDBACK schreibe 1 bis 2 kurze, ermutigende Sätze auf Deutsch, in denen du erklärst, was falsch war und wie es richtig heißt. (Wenn es 'Perfekt' ist, lobe ihn kurz)."
    )
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1,
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        # Fallback falls Groq kurzzeitig überlastet ist
        return "Fehler | Lehrer-KI ist gerade ausgelastet, aber mach einfach weiter!"

def get_groq_response(system_prompt, user_text=None):
    """Holt die Antwort des Gesprächspartners basierend auf dem System Prompt."""
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in st.session_state.history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    if user_text:
        messages.append({"role": "user", "content": user_text})
        
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.1, 
            max_tokens=60
        )
        return completion.choices[0].message.content
    except Exception as e:
        return "Lo siento, error de conexión. Bitte sprich deinen Satz noch einmal!"

def text_to_speech(text):
    """Wandelt Text in Audio um mit Anti-Freeze Schutz."""
    try:
        tts = gTTS(text, lang='es')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        st.session_state.audio_to_play = b64
    except Exception as e:
        st.error("Audio konnte nicht geladen werden (Google-Limit). Bitte lies den Text der KI unten!")
        st.session_state.audio_to_play = None

def transcribe_audio_groq(audio_bytes):
    """Wandelt Audio über das flüssige Whisper-Modell in Text um."""
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            language="es"
        )
        return transcription.text
    except Exception as e:
        return None

def get_system_prompt(words_list, difficulty_level, is_start=False, start_word=None):
    """Baut den perfekten Prompt inklusive strikter Wort-Regeln und Level."""
    all_words_str = ", ".join(words_list)
    base_prompt = (
        f"ABSOLUTES VERBOT: Du bist ein Sprachpartner, aber du darfst AUSSCHLIESSLICH die folgenden Wörter benutzen: [{all_words_str}]. "
        f"Du darfst KEIN EINZIGES WORT verwenden, das nicht in dieser Liste steht. Keine Füllwörter, keine Artikel ('el', 'la', 'un'), keine Ausnahmen! "
        f"Es ist völlig egal, ob deine Grammatik dadurch falsch oder unnatürlich ist. Hauptsache, du nutzt nur diese Wörter! "
    )
    
    if difficulty_level == "🟢 Leicht":
        diff_prompt = "NIVEAU LEICHT: Verwende extrem kurze Sätze (maximal 3-5 Wörter). Stelle sehr simple, direkte Fragen, die leicht zu beantworten sind."
    elif difficulty_level == "🔴 Schwer":
        diff_prompt = "NIVEAU SCHWER: Verwende längere Sätze. Stelle komplexere, offenere Fragen, die den User zum Nachdenken zwingen."
    else: 
        diff_prompt = "NIVEAU MITTEL: Verwende normale Sätze und stelle thematisch passende Fragen."

    if is_start:
        action_prompt = f"STARTE DAS GESPRÄCH: Stelle mir sofort eine Frage. Du MUSST das Wort '{start_word}' in deiner Frage verwenden! Gib exakt EINEN kurzen Satz aus. Generiere keine Listen."
    else:
        action_prompt = "Reagiere kurz auf den User und stelle sofort eine neue Frage. Gib exakt EINEN Satz aus. Generiere keine Listen oder Erklärungen."
        
    return f"{base_prompt} {diff_prompt} {action_prompt}"

# --- APP LAYOUT ---
st.title("🇪🇸 Spanisch Video-Call")
diff_options = ["🟢 Leicht", "🟡 Mittel", "🔴 Schwer"]

# 1. SETUP-BILDSCHIRM
if not st.session_state.call_started:
    st.write("### 📝 Vorbereitung")
    
    current_index = diff_options.index(st.session_state.difficulty) if st.session_state.difficulty in diff_options else 1
    selected_difficulty = st.selectbox(
        "Wähle dein Sprachniveau:",
        diff_options,
        index=current_index
    )
    st.session_state.difficulty = selected_difficulty
    
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
                
                random_start_word = random.choice(words)
                sys_prompt = get_system_prompt(words, st.session_state.difficulty, is_start=True, start_word=random_start_word)
                
                with st.spinner(f"Verbindung wird aufgebaut ({st.session_state.difficulty})..."):
                    ai_reply = get_groq_response(sys_prompt, "Start")
                    st.session_state.history.append({"role": "assistant", "content": ai_reply})
                    save_active_call() 
                    text_to_speech(ai_reply)
                st.rerun()

    with col2:
        saved_call = load_active_call()
        if saved_call:
            if st.button("🔄 Laufenden Call fortsetzen", use_container_width=True):
                st.session_state.history = saved_call["history"]
                st.session_state.vocab_list = saved_call["vocab_list"]
                st.session_state.difficulty = saved_call.get("difficulty", st.session_state.difficulty)
                st.session_state.call_started = True
                st.session_state.last_processed_audio = None
                st.rerun()
        else:
            st.button("🔄 Kein aktiver Call offen", use_container_width=True, disabled=True)

    if past_saved_calls:
        st.write("---")
        st.write("### 📂 Deine gespeicherten Gespräche")
        for i, past_chat in enumerate(reversed(past_saved_calls)):
            with st.expander(f"💾 Gespräch vom {past_chat['date']} (Niveau: {past_chat.get('difficulty', 'Unbekannt')})"):
                for msg in past_chat['history']:
                    if msg["role"] == "user":
                        st.markdown(f"**👤 Du:** {msg['content']}")
                        if "evaluation" in msg:
                            eval_text = msg["evaluation"]
                            try:
                                stufe, feedback = eval_text.split("|", 1)
                                if "Perfekt" in stufe:
                                    st.success(f"✅ **Perfekt:** {feedback.strip()}")
                                elif "Fehler" in stufe:
                                    st.warning(f"⚠️ **Kleiner Fehler:** {feedback.strip()}")
                                else:
                                    st.error(f"❌ **Falsch:** {feedback.strip()}")
                            except:
                                st.info(f"👨‍🏫 **Feedback:** {eval_text}")
                    else:
                        st.markdown(f"**🤖 Groq KI:** {msg['content']}")
                
                if st.button(f"▶️ Dieses Gespräch fortsetzen", key=f"resume_{i}"):
                    st.session_state.history = past_chat['history'].copy()
                    st.session_state.vocab_list = past_chat['vocab_list'].copy()
                    st.session_state.difficulty = past_chat.get("difficulty", st.session_state.difficulty)
                    st.session_state.call_started = True
                    st.session_state.last_processed_audio = None
                    save_active_call()
                    st.rerun()

# 2. CALL-BILDSCHIRM
if st.session_state.call_started:
    st.markdown(f"""
        <div style="background-color: #1E1E1E; border-radius: 20px; padding: 40px; text-align: center; margin-bottom: 20px;">
            <h1 style='font-size: 120px; margin: 0;'>👤</h1>
            <p style="color: #4CAF50; margin-top: 10px;">Groq Video-Call Aktiv <br><small>Niveau: {st.session_state.difficulty}</small></p>
            <small style="color: #888;">Du kannst das Fenster jederzeit schließen. Der Chat wird automatisch gespeichert!</small>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_to_play:
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{st.session_state.audio_to_play}" type="audio/mp3"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)
        st.session_state.audio_to_play = None 
        
    with st.expander("📝 Transkript & Lehrer-Feedback anzeigen", expanded=True):
        for msg in st.session_state.history:
            if msg["role"] == "user":
                st.markdown(f"**👤 Du:** {msg['content']}")
                
                if "evaluation" in msg:
                    eval_text = msg["evaluation"]
                    try:
                        stufe, feedback = eval_text.split("|", 1)
                        if "Perfekt" in stufe:
                            st.success(f"✅ **Perfekt:** {feedback.strip()}")
                        elif "Fehler" in stufe:
                            st.warning(f"⚠️ **Kleiner Fehler:** {feedback.strip()}")
                        else:
                            st.error(f"❌ **Falsch:** {feedback.strip()}")
                    except:
                        st.info(f"👨‍🏫 **Feedback:** {eval_text}")
            else:
                st.markdown(f"**🤖 Groq KI:** {msg['content']}")
            
    st.write("---")
    
    col_text, col_diff = st.columns([2, 1])
    with col_text:
        st.write("### 🎙️ Du bist dran")
    with col_diff:
        current_diff_idx = diff_options.index(st.session_state.difficulty) if st.session_state.difficulty in diff_options else 1
        new_diff = st.selectbox(
            "⚙️ Niveau ändern:",
            diff_options,
            index=current_diff_idx,
            key="active_diff",
            label_visibility="collapsed"
        )
        if new_diff != st.session_state.difficulty:
            st.session_state.difficulty = new_diff
            save_active_call()
            st.rerun()

    audio_value = st.audio_input("Halte den Knopf zum Sprechen:")
    
    if audio_value:
        current_audio_bytes = audio_value.getvalue()
        
        if st.session_state.last_processed_audio != current_audio_bytes:
            st.session_state.last_processed_audio = current_audio_bytes
            
            with st.spinner(f"Groq analysiert deinen Satz..."):
                user_text = transcribe_audio_groq(current_audio_bytes)
                
                if user_text:
                    # Schritt 1: Lehrer-Bewertung (unsichtbar im Hintergrund)
                    evaluation_result = evaluate_spanish_sentence(user_text)
                    
                    # Schritt 2: Speichern von User-Eingabe + Bewertung
                    st.session_state.history.append({
                        "role": "user", 
                        "content": user_text,
                        "evaluation": evaluation_result
                    })
                    save_active_call() 
                    
                    # Schritt 3: Die normale Chat-KI antworten lassen
                    sys_prompt = get_system_prompt(st.session_state.vocab_list, st.session_state.difficulty, is_start=False)
                    ai_reply = get_groq_response(sys_prompt)
                    
                    # Schritt 4: Antwort speichern und vorlesen
                    st.session_state.history.append({"role": "assistant", "content": ai_reply})
                    save_active_call() 
                    text_to_speech(ai_reply)
                    st.rerun()
                else:
                    st.error("Limit erreicht oder Audio nicht erkannt! Bitte warte 3 Sekunden und drücke nochmal auf den Aufnahme-Knopf.")
                    st.session_state.last_processed_audio = None # Erlaubt dir, es sofort nochmal zu versuchen
                
    if st.button("Call beenden & dauerhaft archivieren", type="primary"):
        if st.session_state.history:
            save_completed_call(st.session_state.history, st.session_state.vocab_list, st.session_state.difficulty)
        
        update_streak()
        delete_active_call() 
        st.session_state.call_started = False
        st.session_state.history = []
        st.session_state.last_processed_audio = None
        st.rerun()
