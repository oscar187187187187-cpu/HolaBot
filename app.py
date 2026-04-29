import streamlit as st
import os
from data_manager import load_data, update_xp, add_words_bulk
from ai_manager import get_tutor_response, transcribe_audio, text_to_speech
from audio_recorder_streamlit import audio_recorder

# --- DESIGN & CSS ---
st.set_page_config(page_title="HolaLingo", page_icon="🦉")

st.markdown("""
<style>
   .main { background-color: #f7f7f7; }
   .stButton>button { border-radius: 12px; background-color: #58cc02; color: white; border: none; font-weight: bold; height: 3em; width: 100%; transition: 0.3s; }
   .stButton>button:hover { background-color: #46a302; transform: scale(1.02); }
   .sidebar .sidebar-content { background-color: #ffffff; }
   .user-card { background: white; padding: 20px; border-radius: 15px; border: 2px solid #e5e5e5; margin-bottom: 10px; }
   .streak-fire { color: #ff9600; font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- STATE ---
data = load_data()
if "messages" not in st.session_state: st.session_state.messages = []
if "mode" not in st.session_state: st.session_state.mode = "Konversation"

# --- SIDEBAR (Profil & Pfad) ---
with st.sidebar:
   st.markdown(f"<div class='user-card'><h3>🦉 HolaLingo</h3><p class='streak-fire'>🔥 Streak: {data['streak']} Tage</p></div>", unsafe_allow_html=True)

   level = (data["xp"] // 100) + 1
   xp_in_level = data["xp"] % 100
   st.write(f"**Level {level}**")
   st.progress(xp_in_level / 100)
   st.write(f"⭐ {data['xp']} Gesamte XP")

   st.divider()
   new_mode = st.radio("Lern-Modus:", ["Konversation", "Lernpfad"])
   if new_mode != st.session_state.mode:
       st.session_state.mode = new_mode
       st.session_state.messages = []
       st.rerun()

   with st.expander("📥 Vokabel-Turbo"):
       bulk = st.text_area("Wörter hier rein:")
       if st.button("Importieren"):
           added = add_words_bulk(bulk)
           st.success(f"{added} Wörter gelernt!")
           st.rerun()

# --- CHAT ---
st.title(f"📍 {st.session_state.mode}")

for m in st.session_state.messages:
   with st.chat_message(m["role"]):
       st.write(m["content"])

# INPUT
audio_bytes = audio_recorder(text="", icon_size="2x", neutral_color="#58cc02")
prompt = st.chat_input("Schreib HolaBot...")

user_in = None
if audio_bytes: user_in = transcribe_audio(audio_bytes, "es") # Standard auf Spanisch für Übung
if prompt: user_in = prompt

if user_in:
   st.session_state.messages.append({"role": "user", "content": user_in})
   with st.chat_message("user"): st.write(user_in)

   with st.spinner("Lade..."):
       resp = get_tutor_response(user_in, data, st.session_state.mode)
       update_xp(10) # 10 XP pro Interaktion
       audio_p = text_to_speech(resp)

   with st.chat_message("assistant"):
       st.write(resp)
       if audio_p: st.audio(audio_p, autoplay=True)

   st.session_state.messages.append({"role": "assistant", "content": resp})
   st.rerun()
