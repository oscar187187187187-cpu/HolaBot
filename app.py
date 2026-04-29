import streamlit as st
import os
from data_manager import load_data, update_progress, add_words_bulk
from ai_manager import get_tutor_response, transcribe_audio, text_to_speech
from audio_recorder_streamlit import audio_recorder

# --- STYLING (DUOLINGO LOOK) ---
st.set_page_config(page_title="HolaLingo Ultra", page_icon="🦉", layout="wide")

st.markdown("""
<style>
   body { background-color: #f0f2f5; }
   .unit-circle {
       width: 80px; height: 80px; background-color: #58cc02; border-radius: 50%;
       display: flex; align-items: center; justify-content: center;
       color: white; font-weight: bold; font-size: 20px;
       box-shadow: 0 4px 0 #46a302; margin: 10px auto;
   }
   .unit-locked { background-color: #e5e5e5; box-shadow: 0 4px 0 #afafaf; }
   .path-line { width: 4px; height: 30px; background-color: #e5e5e5; margin: 0 auto; }
   .active-line { background-color: #58cc02; }
   .stat-card { background: white; padding: 15px; border-radius: 12px; border: 2px solid #e5e5e5; text-align: center; }
   .chat-bubble { background: white; padding: 15px; border-radius: 15px; border: 2px solid #e5e5e5; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE & DATA ---
data = load_data()
if "messages_conv" not in st.session_state: st.session_state.messages_conv = []
if "messages_learn" not in st.session_state: st.session_state.messages_learn = []
if "last_audio" not in st.session_state: st.session_state.last_audio = None

# --- SIDEBAR ---
with st.sidebar:
   st.image("https://design-style-guide.freecodecamp.org/img/duolingo-logo.png", width=150) # Platzhalter für Logo
   st.markdown(f"<div class='stat-card'>🔥 {data['streak']} Tage Streak</div>", unsafe_allow_html=True)
   st.markdown(f"<div class='stat-card'>⭐ {data['xp']} XP</div>", unsafe_allow_html=True)

   st.divider()
   app_mode = st.radio("Modus:", ["Konversation", "Lernpfad"])
   mic_lang = st.radio("Sprech-Sprache:", ["Deutsch", "Spanisch"])
   lang_code = "de" if mic_lang == "Deutsch" else "es"

   st.divider()
   with st.expander("📥 Vokabel Massen-Import"):
       bulk = st.text_area("Kopiere hier deine Liste rein (Wort1, Wort2...)")
       if st.button("Jetzt importieren"):
           n = add_words_bulk(bulk)
           st.success(f"{n} neue Wörter gelernt!")
           st.rerun()

   if st.button("🗑️ Chat Verlauf löschen"):
       if app_mode == "Konversation": st.session_state.messages_conv = []
       else: st.session_state.messages_learn = []
       st.rerun()

# --- MAIN LAYOUT (2 Spalten: Pfad & Chat) ---
col_path, col_chat = st.columns([1, 2])

with col_path:
   st.subheader("Dein Lernpfad")
   # Visueller Pfad Generator
   for i in range(1, 6):
       is_active = (i == data["unit"])
       is_done = (i < data["unit"])
       style = "unit-circle" if (is_active or is_done) else "unit-circle unit-locked"
       label = "✅" if is_done else f"U{i}"

       st.markdown(f"<div class='{style}'>{label}</div>", unsafe_allow_html=True)
       if i < 5:
           line_style = "path-line active-line" if is_done else "path-line"
           st.markdown(f"<div class='{line_style}'></div>", unsafe_allow_html=True)

   st.info(f"Unit {data['unit']}: {500 - (data['xp'] % 500)} XP bis zur nächsten Unit!")

with col_chat:
   st.title(f"📍 {app_mode}")

   # Richtigen Chat-Speicher wählen
   msgs = st.session_state.messages_conv if app_mode == "Konversation" else st.session_state.messages_learn

   for m in msgs:
       with st.chat_message(m["role"]):
           st.write(m["content"])
           if "audio" in m: st.audio(m["audio"])

   st.write("---")
   c1, c2 = st.columns([1, 5])
   with c1:
       audio_bytes = audio_recorder(text="", icon_size="2x", neutral_color="#58cc02")
   with c2:
       prompt = st.chat_input("Nachricht...")

   user_in = None
   if audio_bytes and audio_bytes != st.session_state.last_audio:
       st.session_state.last_audio = audio_bytes
       user_in = transcribe_audio(audio_bytes, lang_code)
   if prompt: user_in = prompt

   if user_in:
       msgs.append({"role": "user", "content": user_in})
       with st.chat_message("user"): st.write(user_in)

       with st.spinner("HolaBot schreibt..."):
           response = get_tutor_response(user_in, data, app_mode)
           audio_p = text_to_speech(response)
           update_progress(15) # XP geben

       with st.chat_message("assistant"):
           st.write(response)
           if audio_p: st.audio(audio_p, autoplay=True)

       msgs.append({"role": "assistant", "content": response, "audio": audio_p})
       st.rerun()
