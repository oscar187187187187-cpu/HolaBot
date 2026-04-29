
import streamlit as st
import os
from ai_manager import get_spanish_tutor_response, transcribe_audio, text_to_speech
from data_manager import load_vocab, add_words_bulk, get_user_level
from audio_recorder_streamlit import audio_recorder

st.set_page_config(page_title="HolaBot", page_icon="🇪🇸", layout="centered")

# --- GETRENNTE CHAT VERLÄUFE ---
if "chat_conv" not in st.session_state: st.session_state.chat_conv = []
if "chat_learn" not in st.session_state: st.session_state.chat_learn = []
if "last_audio" not in st.session_state: st.session_state.last_audio = None

# Level berechnen
user_level, word_count = get_user_level()

with st.sidebar:
   st.header(f"🏆 Dein Profil: Level {user_level}")
   st.write(f"Vokabeln gelernt: {word_count}")

   st.divider()
   st.header("🎮 Modus wählen")
   app_mode = st.radio("Was möchtest du tun?", ("Konversation", "Lernen (Neue Wörter)"))

   st.divider()
   st.header("🎤 Mikrofon einstellen")
   st.write("In welcher Sprache sprichst du gleich?")
   mic_lang = st.radio("Sprache:", ("Deutsch", "Spanisch"))
   lang_code = "de" if mic_lang == "Deutsch" else "es"

   st.divider()
   st.header("📚 Massen-Import")
   bulk_input = st.text_area("Vokabeln einfügen (mit Komma oder Enter getrennt):", placeholder="el perro, la casa\ncomer, hola")
   if st.button("➕ Alle Speichern") and bulk_input:
       added = add_words_bulk(bulk_input)
       st.success(f"{added} neue Wörter gespeichert! (Duplikate ignoriert)")
       st.rerun()

   st.divider()
   if st.button("🗑️ Aktuellen Chat löschen"):
       if app_mode == "Konversation": st.session_state.chat_conv = []
       else: st.session_state.chat_learn = []
       st.rerun()

# --- HAUPTBEREICH ---
st.title(f"🇪🇸 HolaBot - {app_mode}")
if app_mode == "Konversation":
   st.write(f"Ich spreche nur mit Wörtern, die du kennst. (Level {user_level})")
else:
   st.write(f"Lass uns neue Wörter für Level {user_level} lernen!")

# Den richtigen Chat anzeigen
current_chat = st.session_state.chat_conv if app_mode == "Konversation" else st.session_state.chat_learn

for msg in current_chat:
   with st.chat_message(msg["role"]):
       st.markdown(msg["content"])
       if msg.get("audio_path") and os.path.exists(msg["audio_path"]):
           st.audio(msg["audio_path"])

st.write("---")
col1, col2 = st.columns([1, 4])
with col1:
   st.write("🎤 Sprechen:")
   audio_bytes = audio_recorder(text="", recording_color="#d32f2f", neutral_color="#4caf50", icon_size="2x")
with col2:
   prompt = st.chat_input("...oder tippe etwas ein!")

user_text = None

if audio_bytes and audio_bytes != st.session_state.last_audio:
   st.session_state.last_audio = audio_bytes
   with st.spinner("Höre zu..."):
       user_text = transcribe_audio(audio_bytes, lang_code)

if prompt:
   user_text = prompt

if user_text:
   current_chat.append({"role": "user", "content": user_text})
   with st.chat_message("user"):
       st.markdown(user_text)

   with st.chat_message("assistant"):
       with st.spinner("HolaBot denkt nach..."):
           vocab = load_vocab()
           response = get_spanish_tutor_response(user_text, vocab, app_mode, user_level)
           st.markdown(response)

           audio_file = text_to_speech(response)
           if audio_file:
               st.audio(audio_file, autoplay=True)

   current_chat.append({"role": "assistant", "content": response, "audio_path": audio_file})
   st.rerun()
