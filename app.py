import streamlit as st
from groq import Groq
import os

# ==========================================
# 1. INITIALISIERUNG & SEITEN-SETUP
# ==========================================
st.set_page_config(
    page_title="Professioneller KI-Sprach-Assistent",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Groq Client initialisieren
# Ersetze "DEIN_GROQ_API_KEY" mit deinem echten Schlüssel, falls du keine Umgebungsvariablen nutzt
GROQ_API_KEY = "DEIN_GROQ_API_KEY"
client = Groq(api_key=GROQ_API_KEY)

# ==========================================
# 2. SESSION STATE MANAGEMENT (Chat-Verlauf)
# ==========================================
# Hier sorgen wir dafür, dass die App sich an das Gespräch erinnert
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "Du bist ein hochentwickelter, freundlicher und präzise antwortender KI-Assistent. Antworte immer auf Deutsch."}
    ]

if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0

# ==========================================
# 3. SEITENLEISTE (SIDEBAR) & EINSTELLUNGEN
# ==========================================
with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.write("Konfiguriere deine KI-Sitzung hier.")
    
    # Modell-Auswahl für Flexibilität
    selected_model = st.selectbox(
        "Chat-Modell wählen:",
        ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
        index=0,
        help="Das 8b-Modell ist extrem schnell, das 70b-Modell ist für komplexe Logik gedacht."
    )
    
    st.divider()
    
    # Status-Anzeige
    st.subheader("📊 Statistik")
    st.write(f"Anzahl Nachrichten im Chat: {len(st.session_state.messages) - 1}")
    
    # Button zum Zurücksetzen des Chats
    if st.button("🔄 Chat-Verlauf löschen", use_container_width=True):
        st.session_state.messages = [
            {"role": "system", "content": "Du bist ein hochentwickelter, freundlicher und präzise antwortender KI-Assistent. Antworte immer auf Deutsch."}
        ]
        st.rerun()

# ==========================================
# 4. HAUPTOBERFLÄCHE (UI) DESIGN
# ==========================================
st.title("🎙️ KI-Sprach-Assistent Pro")
st.write("Nutze die Kraft von Groq Whisper für perfekte Spracherkennung und Llama 3.1 für intelligente Antworten.")

# Container für den Chat-Verlauf (wird dynamisch gerendert)
chat_container = st.container()

# ==========================================
# 5. INPUT-BEREICH (Audio-Aufnahme)
# ==========================================
st.markdown("### 🗣️ Sprich mit der KI")
audio_value = st.audio_input("Klicke auf das Mikrofon, um deine Aufnahme zu starten")

# Variable für den erkannten Text initialisieren
user_text_input = ""

if audio_value:
    audio_bytes = audio_value.read()
    
    # --- SCHRITT A: HOCHPRÄZISE AUDIO-TRANSKRIPTION (Groq Whisper) ---
    with st.spinner("⏳ Whisper analysiert deine Stimme... Bitte warten..."):
        try:
            transcription = client.audio.transcriptions.create(
                file=("live_speech.wav", audio_bytes),
                model="whisper-large-v3",
                response_format="text"
            )
            
            # Wenn die Transkription erfolgreich war, speichern wir den Text
            if transcription and transcription.strip():
                user_text_input = transcription.strip()
            else:
                st.warning("⚠️ Es wurde kein Ton oder Text erkannt. Bitte versuche es noch einmal.")
                
        except Exception as e:
            st.error(f"❌ Fehler bei der Spracherkennung (Groq Whisper): {e}")

# ==========================================
# 6. KI-ANTWORT-LOGIK & VERLAUFS-SPEICHERUNG
# ==========================================
# Wenn wir einen Text aus der Audioaufnahme generiert haben, verarbeiten wir ihn hier
if user_text_input:
    
    # 1. Benutzernachricht dem Chat-Verlauf hinzufügen
    st.session_state.messages.append({"role": "user", "content": user_text_input})
    
    # 2. --- SCHRITT B: TEXT-GENERIERUNG (Llama 3.1) ---
    with st.spinner("🤖 Die KI analysiert den Text und formuliert eine Antwort..."):
        try:
            chat_completion = client.chat.completions.create(
                messages=st.session_state.messages, # Der komplette Verlauf wird mitgesendet!
                model=selected_model,
                temperature=0.7,
                max_tokens=1024
            )
            
            # Antwort auslesen
            ai_response = chat_completion.choices[0].message.content
            
            # 3. KI-Antwort dem Chat-Verlauf hinzufügen
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
        except Exception as e:
            st.error(f"❌ Fehler bei der Generierung der KI-Antwort: {e}")
            # Falls es schiefgeht, entfernen wir die letzte User-Nachricht, damit das System synchron bleibt
            st.session_state.messages.pop()

# ==========================================
# 7. CHAT-HISTORIE AUF DER WEBSEITE ANZEIGEN
# ==========================================
# Wir rendern den Verlauf im dafür vorgesehenen Container ganz oben, damit es wie ein echter Chat aussieht
with chat_container:
    for msg in st.session_state.messages:
        # System-Prompts überspringen wir in der Anzeige
        if msg["role"] == "system":
            continue
            
        # Chat-Blasen je nach Rolle anzeigen
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.write(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(msg["content"])

# Fußzeile
st.markdown("---")
st.caption("Entwickelt mit Streamlit, Groq Whisper-v3 und Llama-3.1 AI Modellen. Schnell. Präzise. Stabil.")
