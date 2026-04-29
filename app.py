import streamlit as st
import os
from ai_manager import get_spanish_tutor_response, transcribe_audio, text_to_speech
from data_manager import load_vocab, add_duolingo_words
from audio_recorder_streamlit import audio_recorder

st.set_page_config(page_title="HolaBot", page_icon="🇪🇸", layout="centered")
st.title("🇪🇸 HolaBot: Dein Sprachlehrer")

if "messages" not in st.session_state:
   st.session_state.messages = []
if "last_audio" not in st.session_state:
   st.session_state.last_audio = None

# --- EINSTELLUNGEN & MODI ---
with st.sidebar:
   st.header("🎮 Modus wählen")
   app_mode = st.radio("Was möchtest du tun?", ("Konversation", "Lernen (Neue Wörter)"))

   st.divider()
   st.header("📚 Dein Wortschatz")
   new_word = st.text_input("Wort hinzufügen:")
   if st.button("➕ Speichern") and new_word:
       add_duolingo_words([new_word.strip()])
       st.success(f"'{new_word}' gespeichert!")

   vocab_data = load_vocab()
   with st.expander(f"Alle Wörter ({len(vocab_data.get('known_words', []))})"):
       st.write(", ".join(vocab_data.get('known_words', [])) if vocab_data.get('known_words') else "Keine Wörter.")

   st.divider()
   if st.button("🗑️ Chat löschen"):
       st.session_state.messages = []
       st.rerun()

# --- CHAT & AUDIO BEREICH ---
for msg in st.session_state.messages:
   with st.chat_message(msg["role"]):
       st.markdown(msg["content"])
       if msg.get("audio_path") and os.path.exists(msg["audio_path"]):
           st.audio(msg["audio_path"])

st.write("---")
col1, col2 = st.columns([1, 4])
with col1:
   st.write("🎤 Sprechen:")
   # Mikrofon-Button für den Nutzer
   audio_bytes = audio_recorder(text="", recording_color="#d32f2f", neutral_color="#4caf50", icon_size="2x")
with col2:
   # Text-Feld als Alternative
   prompt = st.chat_input("...oder tippe etwas ein!")

# --- LOGIK ---
user_text = None

# Wenn Sprachnachricht aufgenommen wurde
if audio_bytes and audio_bytes != st.session_state.last_audio:
   st.session_state.last_audio = audio_bytes
   with st.spinner("Höre zu..."):
       user_text = transcribe_audio(audio_bytes)

# Wenn Text eingegeben wurde
if prompt:
   user_text = prompt

# Antwort generieren
if user_text:
   st.session_state.messages.append({"role": "user", "content": user_text})
   with st.chat_message("user"):
       st.markdown(user_text)

   with st.chat_message("assistant"):
       with st.spinner("HolaBot denkt nach..."):
           vocab = load_vocab()
           response = get_spanish_tutor_response(user_text, vocab, app_mode)
           st.markdown(response)

           # Stimme generieren
           audio_file = text_to_speech(response)
           if audio_file:
               st.audio(audio_file, autoplay=True)

   st.session_state.messages.append({"role": "assistant", "content": response, "audio_path": audio_file})
   st.rerun()
