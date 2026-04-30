import streamlit as st
import os
from data_manager import (load_data, save_data, add_words_bulk, delete_word, 
                          get_unit_structure, check_streak, get_smart_words)
from ai_manager import get_ai_response, transcribe_audio, text_to_speech
from audio_recorder_streamlit import audio_recorder

# --- DESIGN SETUP ---
st.set_page_config(page_title="PeakLingo", layout="wide")

def local_css():
    st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    /* HabitPeak Card Design */
    .peak-card {
        background: #ffffff;
        padding: 25px;
        border-radius: 24px;
        box-shadow: 10px 10px 30px #d1d9e6, -10px -10px 30px #ffffff;
        margin-bottom: 25px;
        border: 1px solid rgba(255,255,255,0.3);
    }
    .stat-card { text-align: center; }
    .stat-val { font-size: 32px; font-weight: 800; color: #1e293b; }
    .stat-label { font-size: 12px; text-transform: uppercase; color: #64748b; letter-spacing: 1px; }
    
    /* Lernpfad Nodes */
    .node-container { display: flex; flex-direction: column; align-items: center; }
    .unit-node {
        width: 70px; height: 70px; border-radius: 35px;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold; margin: 10px 0; border: 4px solid #fff;
    }
    .node-done { background-color: #10b981; color: white; box-shadow: 0 4px 15px rgba(16,185,129,0.3); }
    .node-active { background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; transform: scale(1.1); box-shadow: 0 8px 20px rgba(59,130,246,0.4); }
    .node-locked { background-color: #e2e8f0; color: #94a3b8; }
    .path-line { width: 6px; height: 30px; background-color: #e2e8f0; }
    .line-active { background-color: #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- INITIALISIERUNG ---
data = check_streak()
if "msgs_learn" not in st.session_state: st.session_state.msgs_learn = []
if "msgs_sandbox" not in st.session_state: st.session_state.msgs_sandbox = []

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 🏔️ PeakLingo")
    st.divider()
    
    with st.expander("📥 Vokabel-Tresor"):
        cat = st.selectbox("Kategorie", ["Reise", "Essen", "Geschäfte", "Verwandte", "Allgemein"])
        bulk = st.text_area("Bulk Import (Kommagetrennt)")
        if st.button("Hinzufügen"):
            count = add_words_bulk(bulk, cat)
            st.success(f"{count} Wörter importiert!")
            st.rerun()
            
    st.markdown("### 📚 Dein Wortschatz")
    f_cat = st.selectbox("Filter", ["Alle", "Reise", "Essen", "Geschäfte", "Verwandte", "Allgemein"])
    for v in data["vocab"]:
        if f_cat == "Alle" or v["cat"] == f_cat:
            c1, c2 = st.columns([4, 1])
            c1.caption(f"{v['word']} ({v['cat']})")
            if c2.button("🗑️", key=f"del_{v['word']}"):
                delete_word(v['word'])
                st.rerun()

# --- HEADER STATS ---
col1, col2, col3 = st.columns(3)
with col1: st.markdown(f"<div class='peak-card stat-card'><div class='stat-label'>Erfahrung</div><div class='stat-val'>⭐ {data['xp']}</div></div>", unsafe_allow_html=True)
with col2: st.markdown(f"<div class='peak-card stat-card'><div class='stat-label'>Streak</div><div class='stat-val'>🔥 {data['streak']}</div></div>", unsafe_allow_html=True)
with col3: st.markdown(f"<div class='peak-card stat-card'><div class='stat-label'>Wortschatz</div><div class='stat-val'>📚 {len(data['vocab'])}</div></div>", unsafe_allow_html=True)

# --- TABS ---
t_path, t_sandbox = st.tabs(["📍 Lernpfad", "💬 Sandbox"])

with t_path:
    cp_path, cp_chat = st.columns([1, 3])
    units = get_unit_structure()
    curr_u_idx = data["completed_lessons"] // 5

    with cp_path:
        st.markdown("<div class='node-container'>", unsafe_allow_html=True)
        for i in range(len(units) + 1):
            if i < curr_u_idx:
                st.markdown("<div class='unit-node node-done'>✓</div>", unsafe_allow_html=True)
            elif i == curr_u_idx:
                st.markdown("<div class='unit-node node-active'>HIER</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='unit-node node-locked'>LOCKED</div>", unsafe_allow_html=True)
            if i < len(units):
                st.markdown(f"<div class='path-line {'line-active' if i < curr_u_idx else ''}'></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with cp_chat:
        if not units or curr_u_idx >= len(units):
            st.warning("Füge mehr Wörter hinzu, um den Pfad zu generieren!")
        else:
            u_words = units[curr_u_idx]["words"]
            l_types = ["Einführung", "Übung", "Hörverstehen", "Sprech-Test", "Master-Test"]
            curr_type = l_types[data["completed_lessons"] % 5]
            
            st.markdown(f"<div class='peak-card'><b>Lektion:</b> {curr_type} <br> <b>Wörter:</b> {', '.join(u_words)}</div>", unsafe_allow_html=True)
            
            for m in st.session_state.msgs_learn:
                with st.chat_message(m["role"]): st.write(m["content"])
            
            aud = audio_recorder(text="Sprechen", icon_size="2x", neutral_color="#3b82f6", key="rec_l")
            txt = st.chat_input("Schreibe hier...")
            
            final_in = txt
            if aud: final_in = transcribe_audio(aud, "es")
            
            if final_in:
                st.session_state.msgs_learn.append({"role": "user", "content": final_in})
                resp = get_ai_response(final_in, "Lernen", {"type": curr_type, "words": u_words}, st.session_state.msgs_learn)
                st.session_state.msgs_learn.append({"role": "assistant", "content": resp})
                
                # Progress Update
                data["xp"] += 20
                today_str = str(date.today())
                if data["last_login"] != today_str:
                    data["streak"] += 1
                    data["last_login"] = today_str
                save_data(data)
                st.rerun()
            
            if st.button("Lektion beendet ✅"):
                data["completed_lessons"] += 1
                save_data(data)
                st.session_state.msgs_learn = []
                st.balloons()
                st.rerun()

with t_sandbox:
    st.markdown("<div class='peak-card'>Hier nutzt die KI nur Wörter aus deinem Tresor. Fehler werden auf Deutsch erklärt.</div>", unsafe_allow_html=True)
    for m in st.session_state.msgs_sandbox:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    aud_s = audio_recorder(text="Sprechen", icon_size="2x", neutral_color="#10b981", key="rec_s")
    txt_s = st.chat_input("Plaudere auf Spanisch...")
    
    final_s = txt_s
    if aud_s: final_s = transcribe_audio(aud_s, "es")
    
    if final_s:
        st.session_state.msgs_sandbox.append({"role": "user", "content": final_s})
        v_list = [v["word"] for v in data["vocab"]]
        resp_s = get_ai_response(final_s, "Sandbox", {"vocab": v_list}, st.session_state.msgs_sandbox)
        st.session_state.msgs_sandbox.append({"role": "assistant", "content": resp_s})
        
        audio_file = text_to_speech(resp_s)
        if audio_file: st.audio(audio_file, autoplay=True)
        st.rerun()
