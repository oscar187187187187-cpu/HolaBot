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
    client = Groq(api_key=GROQ_API_KEY, max_retries=1, timeout=15.0)
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
        "difficulty": st.session_state.difficulty,
        "used_questions": st.session_state.get("used_questions", [])
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
if "used_questions" not in st.session_state:
    st.session_state.used_questions = []
if "processing" not in st.session_state:
    st.session_state.processing = False

streak_info = load_streak()
past_saved_calls = load_past_calls()

# --- SIDEBAR DISPLAY ---
st.sidebar.title("📊 Dein Fortschritt")
st.sidebar.markdown(f"### 🔥 Streak: **{streak_info['streak']} Tage**")
if streak_info['last_date'] == datetime.now().date().isoformat():
    st.sidebar.success("✅ Heute schon gelernt!")
else:
    st.sidebar.warning("⚡ Heute noch nicht gelernt!")

# --- ANTI-ECHO HILFSFUNKTIONEN ---
def is_echo(user_text, ai_text):
    """Prüft ob die KI den User einfach wiederholt."""
    if not user_text or not ai_text:
        return False
    user_clean = re.sub(r'[^\w\s]', '', user_text.lower()).strip()
    ai_clean = re.sub(r'[^\w\s]', '', ai_text.lower()).strip()
    if not user_clean or not ai_clean:
        return False
    user_words = user_clean.split()
    ai_words = ai_clean.split()
    if len(user_words) <= 2:
        return False
    matches = sum(1 for w in user_words if w in ai_words)
    return (matches / len(user_words)) > 0.5

def generate_fallback_question(words_list, difficulty_level, used_questions):
    """Generiert eine Fallback-Frage wenn die KI echoing macht."""
    templates_easy = [
        "¿Qué te gusta?",
        "¿Dónde estás?",
        "¿Cómo estás?",
        "¿Qué es esto?",
        "¿Te gusta {word}?",
        "¿Tienes {word}?",
        "¿Quieres {word}?"
    ]
    templates_medium = [
        "¿Por qué te gusta {word}?",
        "¿Dónde encuentras {word}?",
        "¿Cuándo usas {word}?",
        "¿Con quién hablas de {word}?",
        "¿Qué piensas sobre {word}?"
    ]
    templates_hard = [
        "¿Por qué crees que {word} es importante?",
        "¿Cómo cambia tu día sin {word}?",
        "¿Dónde prefieres buscar {word} y por qué?",
        "¿Qué harías si no tuvieras {word}?"
    ]
    
    if difficulty_level == "🟢 Leicht":
        templates = templates_easy
    elif difficulty_level == "🔴 Schwer":
        templates = templates_hard
    else:
        templates = templates_medium
    
    for _ in range(10):
        template = random.choice(templates)
        word = random.choice(words_list)
        question = template.format(word=word)
        if question not in used_questions:
            return question
    return "¿Qué te gusta?"

# --- ZENTRALE KI & AUDIO FUNKTIONEN ---

def get_integrated_response(user_text, words_list, difficulty_level, is_start=False, start_word=None, used_questions=None):
    """
    Kombiniert Lehrer-Feedback und Gesprächsantwort in einem JSON-API-Call.
    """
    if used_questions is None:
        used_questions = []
    
    all_words_str = ", ".join(words_list)
    used_questions_str = " | ".join(used_questions[-8:]) if used_questions else "Noch keine"
    
    base_prompt = (
        "Du bist ein spanischer Sprachpartner für einen Deutschsprachigen. "
        "Du führst ein GESPRÄCH auf Spanisch. "
        "WICHTIG: Antworte NUR im JSON-Format!\n\n"
        f"ERLAUBTE WÖRTER (nur diese verwenden): [{all_words_str}]\n"
        "Keine anderen Wörter! Keine Artikel, Konjunktionen oder Präpositionen die nicht in der Liste stehen!\n\n"
        "=== ABSOLUTE REGELN ===\n"
        "1. ECHO-VERBOT: Wiederhole NIEMALS den Satz des Users. "
        "Reagiere NIEMALS mit 'A mí también...' oder 'Yo también...' auf das, was der User gesagt hat. "
        "Stelle stattdessen eine NEUE, UNBEKANNTE Frage.\n"
        "2. FRAGEN-VERBOT: Beantworte deine Frage NICHT selbst. "
        "Du darfst nur FRAGEN stellen, keine Aussagen über dich machen.\n"
        "3. NEUHEIT: Stelle eine Frage die NOCH NICHT in diesem Gespräch gestellt wurde.\n"
        "4. FRAGEZEICHEN: Jede spanische Antwort MUSS mit ? enden.\n"
    )
    
    if difficulty_level == "🟢 Leicht":
        diff_prompt = (
            "\nNIVEAU LEICHT: Sehr kurze Fragen (3-5 Wörter). Einfache Ja/Nein-Fragen oder "
            "'Was...?' / 'Wie...?' Fragen. Nutze nur die einfachsten erlaubten Wörter."
        )
    elif difficulty_level == "🔴 Schwer":
        diff_prompt = (
            "\nNIVEAU SCHWER: Längere Fragen (6-10 Wörter). Offene Fragen die zum Nachdenken anregen. "
            "Verwende verschiedene Fragewörter. Die Frage MUSS mit ? enden."
        )
    else: 
        diff_prompt = (
            "\nNIVEAU MITTEL: Normale Fragen (4-7 Wörter). Stelle eine neue, thematisch passende Frage. "
            "Die Frage MUSS mit ? enden."
        )

    if is_start:
        action_prompt = f"\n\nSTARTE das Gespräch mit einer Frage. Du MUSST das Wort '{start_word}' verwenden!"
    else:
        action_prompt = (
            "\n\nAUFGABE 1: Bewerte den Satz des Users. Wähle: 'Perfekt' (alles richtig), "
            "'Leichter Fehler' (verständlich, kleine Fehler), oder 'Falsch' (ergibt keinen Sinn). "
            "Gib 1-2 Sätze Feedback auf Deutsch.\n"
            "AUFGABE 2: Stelle eine NEUE Frage auf Spanisch. "
            "Die Frage darf NICHT eine Variation der vorherigen Fragen sein.\n"
            f"BEREITS GESTELLTE FRAGEN (diese NICHT wiederholen): {used_questions_str}"
        )

    examples = (
        "\n\n=== BEISPIELE ===\n"
        "User: 'Me gusta el agua.'\n"
        "SCHLECHT: 'A mí también me gusta el agua. ¿Y a ti?' (ECHO! Wiederholt das Thema!)\n"
        "GUT: '¿Dónde bebes el agua?' (Neue Frage, neues Thema!)\n\n"
        "User: 'Hola, ¿cómo estás?'\n"
        "SCHLECHT: 'Hola, estoy bien. ¿Y tú?' (ECHO! Wiederholt Begrüßung!)\n"
        "GUT: '¿Te gusta el café?' (Komplett neue Frage!)\n\n"
        "User: 'Estoy bien, gracias.'\n"
        "SCHLECHT: 'Me alegro. ¿Qué haces?' (Zu ähnlich!)\n"
        "GUT: '¿Dónde vives?' (Neue Richtung!)"
    )
    
    json_instruction = (
        "\n\n=== JSON FORMAT ===\n"
        "{\n"
        '  "stufe": "Perfekt" oder "Leichter Fehler" oder "Falsch",\n'
        '  "feedback": "Deutsches Feedback (1-2 Sätze). Was war falsch und wie richtig? Oder Lob.",\n'
        '  "antwort": "NUR eine neue spanische FRAGE. Nur erlaubte Wörter. Muss mit ? enden. KEINE Aussagen!"\n'
        "}"
    )
    
    system_prompt = base_prompt + diff_prompt + action_prompt + examples + json_instruction

    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in st.session_state.history[-3:]:
        if "content" in msg and msg["role"] in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    if user_text:
        messages.append({"role": "user", "content": user_text})
        
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        response_data = json.loads(completion.choices[0].message.content)
        
        ai_antwort = response_data.get("antwort", "¿Perdón?")
        
        # Anti-Echo Check
        if not is_start and is_echo(user_text, ai_antwort):
            response_data["antwort"] = generate_fallback_question(words_list, difficulty_level, used_questions)
            response_data["feedback"] += " (Die KI wollte echoen, Fallback-Frage wurde genutzt.)"
        
        # Sicherstellen dass es mit ? endet
        if not response_data.get("antwort", "").strip().endswith("?"):
            response_data["antwort"] = response_data.get("antwort", "¿Perdón?").strip() + "?"
            
        return response_data
        
    except Exception as e:
        return {
            "stufe": "Fehler",
            "feedback": "Verbindungsproblem mit Groq. Bitte sprich deinen Satz noch einmal!",
            "antwort": "¿Perdón, error de conexión?"
        }

def text_to_speech(text):
    """Wandelt Text in Audio um."""
    try:
        tts = gTTS(text, lang='es')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        st.session_state.audio_to_play = b64
    except Exception as e:
        st.session_state.audio_to_play = None

def transcribe_audio_groq(audio_bytes):
    """Wandelt Audio über Whisper in Text um."""
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            language="es"
        )
        return transcription.text
    except Exception as e:
        return None

# --- UI HILFSFUNKTION FÜR FEEDBACK ---
def render_feedback(eval_text):
    """Wertet den Feedback-String aus und zeigt die richtige Box (Grün/Gelb/Rot) an."""
    try:
        stufe, feedback = eval_text.split("|", 1)
        if "Perfekt" in stufe:
            st.success(f"✅ **Perfekt:** {feedback.strip()}")
        elif "Leichter Fehler" in stufe or "Fehler" in stufe:
            st.warning(f"⚠️ **Kleiner Fehler:** {feedback.strip()}")
        else:
            st.error(f"❌ **Falsch:** {feedback.strip()}")
    except:
        st.info(f"👨‍🏫 **Feedback:** {eval_text}")

# --- BROWSER-SICHERES AUDIO WIDGET ---
def play_audio_widget(audio_b64, text_display):
    """Zeigt einen Audio-Player mit Fallback an."""
    if audio_b64:
        st.audio(f"data:audio/mp3;base64,{audio_b64}", format="audio/mp3")
    st.markdown(f"**🤖 KI sagt:** *{text_display}*")

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
                st.session_state.used_questions = []
                st.session_state.processing = False
                save_vocab(vocab_input) 
                
                random_start_word = random.choice(words)
                
                with st.spinner(f"Verbindung wird aufgebaut ({st.session_state.difficulty})..."):
                    response_data = get_integrated_response(
                        "Start", words, st.session_state.difficulty, 
                        is_start=True, start_word=random_start_word
                    )
                    ai_reply = response_data.get("antwort", "¿Hola, qué tal?")
                    
                    st.session_state.history.append({"role": "assistant", "content": ai_reply})
                    st.session_state.used_questions.append(ai_reply)
                    text_to_speech(ai_reply)
                    save_active_call()
                st.rerun()

    with col2:
        saved_call = load_active_call()
        if saved_call:
            if st.button("🔄 Laufenden Call fortsetzen", use_container_width=True):
                st.session_state.history = saved_call["history"]
                st.session_state.vocab_list = saved_call["vocab_list"]
                st.session_state.difficulty = saved_call.get("difficulty", st.session_state.difficulty)
                st.session_state.used_questions = saved_call.get("used_questions", [])
                st.session_state.call_started = True
                st.session_state.last_processed_audio = None
                st.session_state.processing = False
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
                            render_feedback(msg["evaluation"])
                    else:
                        st.markdown(f"**🤖 Groq KI:** {msg['content']}")
                
                if st.button(f"▶️ Dieses Gespräch fortsetzen", key=f"resume_{i}"):
                    st.session_state.history = past_chat['history'].copy()
                    st.session_state.vocab_list = past_chat['vocab_list'].copy()
                    st.session_state.difficulty = past_chat.get("difficulty", st.session_state.difficulty)
                    st.session_state.used_questions = [msg["content"] for msg in past_chat['history'] if msg["role"] == "assistant"]
                    st.session_state.call_started = True
                    st.session_state.last_processed_audio = None
                    st.session_state.processing = False
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
    
    # Audio anzeigen (Browser-kompatibel mit Play-Button)
    if st.session_state.audio_to_play:
        play_audio_widget(st.session_state.audio_to_play, st.session_state.history[-1]["content"] if st.session_state.history else "")
        st.session_state.audio_to_play = None
    elif st.session_state.history and st.session_state.history[-1]["role"] == "assistant":
        # Wenn kein Audio da ist aber eine KI-Antwort existiert, Text anzeigen
        st.markdown(f"**🤖 KI sagt:** *{st.session_state.history[-1]['content']}*")
        
    with st.expander("📝 Transkript & Lehrer-Feedback anzeigen", expanded=True):
        for msg in st.session_state.history:
            if msg["role"] == "user":
                st.markdown(f"**👤 Du:** {msg['content']}")
                if "evaluation" in msg:
                    render_feedback(msg["evaluation"])
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

    # Audio Input - nur wenn nicht gerade verarbeitet wird
    if not st.session_state.processing:
        audio_value = st.audio_input("Halte den Knopf zum Sprechen:")
        
        if audio_value:
            current_audio_bytes = audio_value.getvalue()
            
            if st.session_state.last_processed_audio != current_audio_bytes:
                st.session_state.last_processed_audio = current_audio_bytes
                st.session_state.processing = True
                st.rerun()  # Nur ein rerun um in den processing-Modus zu kommen
    else:
        # Wir sind im Processing-Modus
        st.info("⏳ Groq analysiert deinen Satz...")
        
        # Hole das letzte Audio aus dem State
        if st.session_state.last_processed_audio:
            user_text = transcribe_audio_groq(st.session_state.last_processed_audio)
            
            if user_text:
                response_data = get_integrated_response(
                    user_text, st.session_state.vocab_list, 
                    st.session_state.difficulty, is_start=False,
                    used_questions=st.session_state.used_questions
                )
                
                stufe_aus_json = response_data.get("stufe", "Falsch")
                feedback_aus_json = response_data.get("feedback", "Kein Feedback erhalten.")
                ai_reply = response_data.get("antwort", "¿Perdón?")
                
                eval_string_fuer_ui = f"{stufe_aus_json} | {feedback_aus_json}"
                
                st.session_state.history.append({
                    "role": "user", 
                    "content": user_text,
                    "evaluation": eval_string_fuer_ui
                })
                
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                st.session_state.used_questions.append(ai_reply)
                
                text_to_speech(ai_reply)
                st.session_state.processing = False
                save_active_call()
                st.rerun()
            else:
                st.error("Audio nicht erkannt. Bitte versuche es noch einmal!")
                st.session_state.last_processed_audio = None
                st.session_state.processing = False
                st.rerun()
        else:
            st.session_state.processing = False
                
    if st.button("Call beenden & dauerhaft archivieren", type="primary"):
        if st.session_state.history:
            save_completed_call(st.session_state.history, st.session_state.vocab_list, st.session_state.difficulty)
        
        update_streak()
        delete_active_call() 
        st.session_state.call_started = False
        st.session_state.history = []
        st.session_state.last_processed_audio = None
        st.session_state.used_questions = []
        st.session_state.processing = False
        st.rerun()
