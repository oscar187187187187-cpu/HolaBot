import streamlit as st
import os
from data_manager import load_data, save_data, add_words_bulk, delete_word, get_units, update_xp_and_streak
from ai_manager import get_smart_response, text_to_speech, transcribe_audio
from audio_recorder_streamlit import audio_recorder

# ==========================================
# 1. SEITEN-SETUP & PREMIUM CSS (HabitPeak)
# ==========================================
st.set_page_config(page_title="HolaLingo Peak", page_icon="🏔️", layout="wide")

st.markdown("""
<style>
    /* Hintergrund und generelle Schrift */
    [data-testid="stAppViewContainer"] { background-color: #f3f4f6; font-family: 'Inter', sans-serif; }
    
    /* HabitPeak Cards */
    .peak-card { 
        background: #ffffff; padding: 25px; border-radius: 20px; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.03); border: 1px solid #e5e7eb; 
        margin-bottom: 20px; text-align: center; transition: all 0.3s ease;
    }
    .peak-card:hover { transform: translateY(-3px); box-shadow: 0 15px 30px rgba(0,0,0,0.06); }
    
    /* Stat-Texte */
    .stat-value { font-size: 36px; font-weight: 900; color: #111827; margin-bottom: 5px; }
    .stat-label { font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 1.5px; }
    
    /* Lernpfad Nodes (Kreise) */
    .path-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .unit-node { 
        width: 70px; height: 70px; border-radius: 50%; display: flex; 
        align-items: center; justify-content: center; font-weight: 800; font-size: 18px;
        margin: 10px 0; position: relative; z-index: 2; transition: all 0.3s;
    }
    .node-active { background: linear-gradient(135deg, #10b981 0%, #047857 100%); color: white; box-shadow: 0 0 20px rgba(16, 185, 129, 0.5); border: 4px solid #d1fae5; }
    .node-done { background: #10b981; color: white; border: 4px solid #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .node-locked { background: #e5e7eb; color: #9ca3af; border: 4px solid #f3f4f6; }
    
    /* Verbindungslinien im Pfad */
    .path-line { width: 6px; height: 40px; background: #e5e7eb; margin: -15px 0; z-index: 1; }
    .line-done { background: #10b981; }
    
    /* Buttons */
    .stButton>button { border-radius: 12px; font-weight: 600; transition: 0.2s; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATEN & SESSION STATE INIT
# ==========================================
data = load_data()
units = get_units()

if "chat_conv" not in st.session_state: st.session_state.chat_conv = []
if "chat_learn" not in st.session_state: st.session_state.chat_learn = []
if "last_audio_conv" not in st.session_state: st.session_state.last_audio_conv = None
if "last_audio_learn" not in st.session_state: st.session_state.last_audio_learn = None

# Berechnungen für den Fortschritt
current_unit_index = data['completed_lessons'] // 5
current_lesson_in_unit = data['completed_lessons'] % 5
lesson_types = ["NEU LERNEN 1", "NEU LERNEN 2", "WIEDERHOLUNG", "HÖREN", "MASTER-TEST"]
current_lesson_type = lesson_types[current_lesson_in_unit]

# ==========================================
# 3. SIDEBAR: EINSTELLUNGEN & WORT-TRESOR
# ==========================================
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #10b981;'>🏔️ PeakLingo</h1>", unsafe_allow_html=True)
    st.divider()
    
    # Spracheinstellung fürs Mikrofon
    st.markdown("### 🎙️ Mikrofon Sprache")
    mic_lang = st.radio("Was sprichst du gleich?", ["Spanisch", "Deutsch"], horizontal=True)
    lang_code = "de" if mic_lang == "Deutsch" else "es"
    
    st.divider()
    
    # Der Vokabel-Tresor (Ansehen & Löschen)
    st.markdown(f"### 📚 Mein Tresor ({len(data['vocab'])} Wörter)")
    with st.expander("Wörter verwalten"):
        if not data["vocab"]:
            st.info("Noch keine Wörter vorhanden.")
        else:
            for w in sorted(data["vocab"]):
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{w}**")
                if col2.button("❌", key=f"del_{w}"):
                    delete_word(w)
                    st.rerun()
                    
    # Bulk Import
    st.markdown("### 📥 Massen-Import")
    bulk_input = st.text_area("Wörter einfügen (mit Komma getrennt):", placeholder="el gato, el perro, comer...")
    if st.button("🚀 Speichern") and bulk_input:
        added = add_words_bulk(bulk_input)
        st.success(f"{added} neue Wörter gespeichert!")
        st.rerun()
        
    st.divider()
    if st.button("🗑️ Chats leeren"):
        st.session_state.chat_conv = []
        st.session_state.chat_learn = []
        st.rerun()

# ==========================================
# 4. TOP-DASHBOARD (HabitPeak Stats)
# ==========================================
c1, c2, c3 = st.columns(3)
c1.markdown(f"<div class='peak-card'><div class='stat-value'>⭐ {data['path_xp']}</div><div class='stat-label'>Gesamt XP</div></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='peak-card'><div class='stat-value'>🔥 {data['streak']}</div><div class='stat-label'>Tage Streak</div></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='peak-card'><div class='stat-value'>📖 {len(data['vocab'])}</div><div class='stat-label'>Wörter im Tresor</div></div>", unsafe_allow_html=True)

# ==========================================
# 5. HAUPTBEREICH (TABS)
# ==========================================
tab1, tab2 = st.tabs(["📍 LERNPFAD (Sammle XP)", "💬 FREIE KONVERSATION (Strenge KI)"])

# ------------------------------------------
# TAB 1: DER LERNPFAD
# ------------------------------------------
with tab1:
    col_path, col_action = st.columns([1, 3])
    
    # LINKE SPALTE: Visueller Pfad
    with col_path:
        st.markdown("<h3 style='text-align: center;'>Dein Weg</h3>", unsafe_allow_html=True)
        st.markdown("<div class='path-container'>", unsafe_allow_html=True)
        
        if not units:
            st.warning("Importiere Wörter in der Sidebar, um Units zu generieren!")
        else:
            for i, u in enumerate(units):
                is_done = i < current_unit_index
                is_active = i == current_unit_index
                
                if is_done: style = "node-done"
                elif is_active: style = "node-active"
                else: style = "node-locked"
                
                label = "✅" if is_done else f"U{u['id']}"
                st.markdown(f"<div class='unit-node {style}'>{label}</div>", unsafe_allow_html=True)
                
                # Linie zwischen den Nodes zeichnen (außer beim letzten)
                if i < len(units) - 1:
                    line_style = "line-done" if is_done else ""
                    st.markdown(f"<div class='path-line {line_style}'></div>", unsafe_allow_html=True)
                    
        st.markdown("</div>", unsafe_allow_html=True)

    # RECHTE SPALTE: Aktuelle Lektion
    with col_action:
        if units:
            # Sicherheits-Check, falls alle Units beendet sind
            if current_unit_index >= len(units):
                st.success("🎉 Du hast alle aktuellen Units abgeschlossen! Füge neue Wörter hinzu.")
            else:
                active_unit = units[current_unit_index]
                words_str = ", ".join(active_unit['words'])
                
                # Lektions-Kopf
                st.markdown(f"""
                <div class='peak-card' style='text-align: left;'>
                    <h2 style='color: #10b981;'>Unit {active_unit['id']} - Lektion {current_lesson_in_unit + 1}/5</h2>
                    <h4>Fokus: {current_lesson_type}</h4>
                    <p style='color: #6b7280;'>Diese Wörter sind relevant: <b>{words_str}</b></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Chat-Verlauf Rendern
                for msg in st.session_state.chat_learn:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
                
                # Eingabe (Audio & Text)
                st.write("---")
                rc1, rc2 = st.columns([1, 6])
                with rc1: 
                    audio_learn = audio_recorder(text="", icon_size="2x", neutral_color="#10b981")
                with rc2: 
                    text_learn = st.chat_input("Deine Antwort für den Lernpfad...")
                
                user_input_learn = None
                if audio_learn and audio_learn != st.session_state.last_audio_learn:
                    st.session_state.last_audio_learn = audio_learn
                    with st.spinner("Transkribiere..."):
                        user_input_learn = transcribe_audio(audio_learn, lang_code)
                if text_learn: user_input_learn = text_learn
                
                # KI Antwort verarbeiten
                if user_input_learn:
                    st.session_state.chat_learn.append({"role": "user", "content": user_input_learn})
                    with st.chat_message("user"): st.markdown(user_input_learn)
                    
                    with st.spinner("HolaBot wertet aus..."):
                        ctx = {"lesson_type": current_lesson_type, "unit_words": words_str}
                        resp = get_smart_response(user_input_learn, "Lernpfad", ctx, st.session_state.chat_learn)
                        
                        # XP vergeben!
                        update_xp_and_streak(20)
                        
                        audio_path = text_to_speech(resp)
                    
                    with st.chat_message("assistant"):
                        st.markdown(resp)
                        if audio_path: st.audio(audio_path, autoplay=True)
                    
                    st.session_state.chat_learn.append({"role": "assistant", "content": resp})
                    st.rerun()

                # Button um in der Unit weiterzugehen
                if st.button("Lektion erfolgreich abgeschlossen? Nächste! ➡️", use_container_width=True):
                    data["completed_lessons"] += 1
                    save_data(data)
                    st.session_state.chat_learn = [] # Chat reset für saubere neue Lektion
                    st.balloons()
                    st.rerun()

# ------------------------------------------
# TAB 2: FREIE KONVERSATION
# ------------------------------------------
with tab2:
    st.markdown("""
    <div class='peak-card'>
        <h3>Freies Training</h3>
        <p>Hier gibt es keine XP. Die KI spricht mit dir <b>ausschließlich</b> mit den Wörtern aus deinem Tresor und korrigiert dich auf Deutsch.</p>
    </div>
    """, unsafe_allow_html=True)
    
    for msg in st.session_state.chat_conv:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
    st.write("---")
    cc1, cc2 = st.columns([1, 6])
    with cc1: 
        audio_conv = audio_recorder(text="", icon_size="2x", neutral_color="#3b82f6")
    with cc2: 
        text_conv = st.chat_input("Plaudere auf Spanisch...")
        
    user_input_conv = None
    if audio_conv and audio_conv != st.session_state.last_audio_conv:
        st.session_state.last_audio_conv = audio_conv
        with st.spinner("Höre zu..."):
            user_input_conv = transcribe_audio(audio_conv, lang_code)
    if text_conv: user_input_conv = text_conv
    
    if user_input_conv:
        st.session_state.chat_conv.append({"role": "user", "content": user_input_conv})
        with st.chat_message("user"): st.markdown(user_input_conv)
        
        with st.spinner("HolaBot tippt..."):
            ctx = {"vocab": data["vocab"]}
            resp_conv = get_smart_response(user_input_conv, "Konversation", ctx, st.session_state.chat_conv)
            audio_path_conv = text_to_speech(resp_conv)
            
        with chat_msg := st.chat_message("assistant"):
            st.markdown(resp_conv)
            if audio_path_conv: st.audio(audio_path_conv, autoplay=True)
            
        st.session_state.chat_conv.append({"role": "assistant", "content": resp_conv})
        st.rerun()
