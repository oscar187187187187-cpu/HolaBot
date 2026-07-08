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
    if used_questions is None:
        used_questions = []

    all_words_str = ", ".join(words_list)
    used_questions_str = " | ".join(used_questions[-8:]) if used_questions else "Noch keine"

    # FIX: Alle Anfuehrungszeichen im Prompt korrekt escapen
    base_prompt = (
        "Du bist ein STRENGER spanischer Sprach-Lehrer fuer einen Deutschsprachigen. "
        "Du bewertest JEDEN Satz penibel genau auf Grammatik, Wortwahl und Satzbau. "
        "WICHTIG: Antworte NUR im JSON-Format!\n\n"
        "=== ABSOLUTES WORT-LIMIT ===\n"
        f"ERLAUBTE WOERTER (NUR diese duerfen verwendet werden): [{all_words_str}]\n\n"
        "REGEL 1: Du darfst in deiner spanischen Antwort AUSSCHLIESSLICH Woerter aus der obigen Liste verwenden. "
        "KEINE Ausnahmen! Keine Artikel, keine Konjunktionen, keine Praepositionen die nicht in der Liste stehen. "
        "Wenn ein Wort nicht exakt in der Liste steht, darfst du es NICHT benutzen.\n\n"
        "REGEL 2: Wenn der User ein Wort verwendet das NICHT in der Liste steht, "
        "dann bewerte das als Falsch und erklaere im Feedback auf Deutsch: "
        "Du hast das Wort X verwendet, aber das ist nicht in deiner Vokabelliste. "
        "Benutze nur diese Woerter: [Liste].\n\n"
        "=== BEWERTUNGS-REGELN (STRENG!) ===\n"
        "Perfekt: NUR wenn der Satz zu 100% grammatikalisch korrekt ist, alle Woerter aus der Liste stammen, "
        "und die Satzstellung perfekt ist. Selbst kleinste Fehler (fehlende Akzente, falsche Artikel, falsche Konjugation) "
        "machen den Satz NICHT perfekt.\n\n"
        "Leichter Fehler: Der Satz ist verstaendlich, aber enthaelt 1-3 kleine Fehler wie: "
        "fehlende Akzente, falsche Artikel, falsche Endungen, kleine Wortfehler. "
        "ODER: Der User hat ein nicht-erlaubtes Wort benutzt, aber der Rest ist ok.\n\n"
        "Falsch: Der Satz enthaelt 4+ Fehler, ist unverstaendlich, oder verwendet Woerter die nicht in der Liste stehen. "
        "ODER: Der Satz wiederholt sich, ist unvollstaendig, oder macht keinen Sinn.\n\n"
        "=== ANTI-ECHO REGELN ===\n"
        "1. Wiederhole NIEMALS den Satz des Users. Stelle eine NEUE, UNBEKANNTE Frage.\n"
        "2. Beantworte deine Frage NICHT selbst. Nur FRAGEN stellen.\n"
        "3. Stelle eine Frage die NOCH NICHT gestellt wurde.\n"
        "4. Jede Antwort MUSS mit ? enden.\n"
        "5. VERWENDE NUR WOERTER AUS DER LISTE!\n"
    )

    if difficulty_level == "🟢 Leicht":
        diff_prompt = (
            "\nNIVEAU LEICHT: Sehr kurze Fragen (3-5 Woerter). Einfache Ja/Nein-Fragen. "
            "NUR erlaubte Woerter verwenden!"
        )
    elif difficulty_level == "🔴 Schwer":
        diff_prompt = (
            "\nNIVEAU SCHWER: Laengere Fragen (6-10 Woerter). Offene Fragen. "
            "NUR erlaubte Woerter verwenden!"
        )
    else: 
        diff_prompt = (
            "\nNIVEAU MITTEL: Normale Fragen (4-7 Woerter). "
            "NUR erlaubte Woerter verwenden!"
        )

    if is_start:
        action_prompt = f"\n\nSTARTE das Gespraech mit einer Frage. Du MUSST das Wort '{start_word}' verwenden!"
    else:
        action_prompt = (
            "\n\nAUFGABE 1: BEWERTE STRENG. Zaehle konkret die Fehler auf. "
            "Pruefe ob ALLE Woerter des Users in der erlaubten Liste stehen. "
            "Wenn ein Wort fehlt, nenne es explizit im Feedback auf Deutsch. "
            "Wenn der User 'me gosta' statt 'me gusta' sagt, ist das Leichter Fehler. "
            "Wenn der User den Satz zweimal wiederholt oder 4+ Fehler macht, ist das Falsch. "
            "NUR bei 0 Fehlern und nur erlaubten Woertern: Perfekt.\n\n"
            "AUFGABE 2: Stelle eine NEUE Frage auf Spanisch. "
            "VERWENDE NUR WOERTER AUS DER LISTE! "
            f"BEREITS GESTELLTE FRAGEN: {used_questions_str}"
        )

    examples = (
        "\n\n=== BEISPIELE FUER BEWERTUNG ===\n"
        "User: 'Me gusta la clase de matematicas.' (angenommen 'matematicas' ist NICHT in der Wortliste)\n"
        "-> Stufe: Falsch | Feedback: Du hast das Wort matematicas verwendet, aber das ist nicht in deiner Vokabelliste. "
        "Benutze nur diese Woerter: [Liste].\n\n"
        "User: 'Me gusta el clase.' (falscher Artikel: 'el' statt 'la')\n"
        "-> Stufe: Leichter Fehler | Feedback: Fast richtig! Es heisst la clase, nicht el clase.\n\n"
        "User: 'Me gusta la clase.' (alles richtig, alle Woerter aus Liste)\n"
        "-> Stufe: Perfekt | Feedback: Sehr gut! Alles korrekt.\n\n"
        "User: 'Me gusta me gusta la clase.' (Wiederholung)\n"
        "-> Stufe: Falsch | Feedback: Du hast den Satz wiederholt. Versuche einen vollstaendigen Satz zu bilden."
    )

    json_instruction = (
        "\n\n=== JSON FORMAT ===\n"
        "{\n"
        '  "stufe": "Perfekt" oder "Leichter Fehler" oder "Falsch",\n'
        '  "feedback": "Konkretes Feedback auf Deutsch. Nenne den EXAKTEN Fehler und die korrekte Version. "
        "Wenn nicht-erlaubte Woerter verwendet wurden, nenne sie explizit.",\n"
        '  "antwort": "NUR eine neue spanische FRAGE. NUR erlaubte Woerter aus der Liste. Mit ? enden."\n'
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
            temperature=0.3,
            max_tokens=250,
            response_format={"type": "json_object"}
        )
        response_data = json.loads(completion.choices[0].message.content)

        ai_antwort = response_data.get("antwort", "¿Perdón?")

        # Pruefe ob KI-Antwort nur erlaubte Woerter enthaelt
        ai_words_clean = re.sub(r'[^\w\s]', '', ai_antwort.lower()).split()
        allowed_words_clean = [w.lower().strip() for w in words_list]

        forbidden_in_ai = [w for w in ai_words_clean if w and w not in allowed_words_clean and len(w) > 2]
        if forbidden_in_ai and not is_start:
            response_data["antwort"] = generate_fallback_question(words_list, difficulty_level, used_questions)
            response_data["feedback"] += f" (Die KI hat nicht-erlaubte Woerter benutzt: {', '.join(forbidden_in_ai)}. Fallback-Frage genutzt.)"

        # Anti-Echo Check
        if not is_start and is_echo(user_text, ai_antwort):
            response_data["antwort"] = generate_fallback_question(words_list, difficulty_level, used_questions)
            response_data["feedback"] += " (Die KI wollte echoen, Fallback-Frage wurde genutzt.)"

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
    try:
        tts = gTTS(text, lang='es')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        st.session_state.audio_to_play = b64
    except Exception as e:
        st.session_state.audio_to_play = None

def transcribe_audio_groq(audio_bytes):
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            language="es"
        )
        return transcription.text
    except Exception as e:
        return None

# --- UI HILFSFUNKTION FUER FEEDBACK ---
def render_feedback(eval_text):
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

# --- AUTOPLAY AUDIO ---
def autoplay_audio(audio_b64):
    if audio_b64:
        audio_html = f"""
        <audio autoplay="autoplay">
            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)

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

    if st.session_state.audio_to_play:
        autoplay_audio(st.session_state.audio_to_play)
        st.session_state.audio_to_play = None

    if st.session_state.history and st.session_state.history[-1]["role"] == "assistant":
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

    if not st.session_state.processing:
        audio_value = st.audio_input("Halte den Knopf zum Sprechen:")

        if audio_value:
            current_audio_bytes = audio_value.getvalue()

            if st.session_state.last_processed_audio != current_audio_bytes:
                st.session_state.last_processed_audio = current_audio_bytes
                st.session_state.processing = True
                st.rerun()
    else:
        st.info("⏳ Groq analysiert deinen Satz...")

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
