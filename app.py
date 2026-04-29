import streamlit as st
from data_manager import load_all_data, save_all_data, delete_word, get_units
from ai_manager import get_lesson_response, text_to_speech
from audio_recorder_streamlit import audio_recorder

st.set_page_config(page_title="HolaLingo Peak", layout="wide")

# --- HABITPEAK STYLING ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; }
    .main-card { background: white; padding: 30px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #eee; }
    .stat-val { font-size: 32px; font-weight: 900; color: #1d1d1f; }
    .stat-label { font-size: 14px; color: #86868b; text-transform: uppercase; letter-spacing: 1px; }
    .unit-node { width: 60px; height: 60px; border-radius: 20px; display: flex; align-items: center; justify-content: center; font-weight: bold; margin: 10px auto; transition: 0.3s; }
    .active-node { background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%); color: white; box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4); }
    .locked-node { background: #f0f0f2; color: #bcbcbc; }
    .stButton>button { border-radius: 15px; border: none; font-weight: bold; padding: 10px 20px; }
</style>
""", unsafe_allow_html=True)

data = load_all_data()

# --- SIDEBAR: Wortschatz-Management ---
with st.sidebar:
    st.markdown("<h1 style='color: #00dbde;'>HabitPeak</h1>", unsafe_allow_html=True)
    
    with st.expander("📚 Mein Wortschatz"):
        for w in data["vocab"]:
            cols = st.columns([3, 1])
            cols[0].text(w)
            if cols[1].button("🗑️", key=f"del_{w}"):
                delete_word(w)
                st.rerun()
                
    bulk = st.text_area("Vokabel-Import (kommagetrennt):")
    if st.button("🚀 Importieren"):
        new_words = [x.strip() for x in bulk.split(",") if x.strip()]
        data["vocab"] = list(set(data["vocab"] + new_words))
        save_all_data(data)
        st.rerun()

# --- KOPFZEILE (Stats) ---
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f"<div class='main-card'><span class='stat-label'>Erfolg (XP)</span><br><span class='stat-val'>{data['path_xp']}</span></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='main-card'><span class='stat-label'>Streak</span><br><span class='stat-val'>🔥 {data['streak']} Tage</span></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='main-card'><span class='stat-label'>Unit</span><br><span class='stat-val'>U {(data['completed_lessons'] // 5) + 1}</span></div>", unsafe_allow_html=True)

# --- NAVIGATION ---
tab_path, tab_chat = st.tabs(["📍 Lernpfad", "💬 Freies Gespräch"])

with tab_path:
    col_map, col_lesson = st.columns([1, 3])
    
    with col_map:
        st.markdown("### Dein Fortschritt")
        units = get_units()
        current_unit_idx = data['completed_lessons'] // 5
        
        for i, u in enumerate(units):
            state = "active-node" if i == current_unit_idx else "locked-node"
            st.markdown(f"<div class='unit-node {state}'>U{u['id']}</div>", unsafe_allow_html=True)
            if i < len(units)-1: st.markdown("<div style='width:2px; height:20px; background:#eee; margin:0 auto;'></div>", unsafe_allow_html=True)

    with col_lesson:
        if not units:
            st.warning("Bitte füge zuerst Vokabeln in der Sidebar hinzu, um deinen Pfad zu generieren!")
        else:
            curr_unit = units[min(current_unit_idx, len(units)-1)]
            lesson_sub_idx = data['completed_lessons'] % 5
            types = ["INTRO", "INTRO", "REVIEW", "LISTENING", "TEST"]
            curr_type = types[lesson_sub_idx]
            
            st.markdown(f"<div class='main-card'><h3>Lektion: {curr_type}</h3><p>Wörter dieser Unit: {', '.join(curr_unit['words'])}</p></div>", unsafe_allow_html=True)
            
            if "lesson_msgs" not in st.session_state: st.session_state.lesson_msgs = []
            
            for m in st.session_state.lesson_msgs:
                with st.chat_message(m["role"]): st.write(m["content"])

            user_input = st.chat_input("Deine Antwort...")
            if user_input:
                st.session_state.lesson_msgs.append({"role": "user", "content": user_input})
                with st.spinner("KI denkt nach..."):
                    resp = get_lesson_response(user_input, curr_type, curr_unit["words"], st.session_state.lesson_msgs[-3:])
                    data["path_xp"] += 20 # XP NUR IM PFAD
                    save_all_data(data)
                    audio = text_to_speech(resp)
                
                st.session_state.lesson_msgs.append({"role": "assistant", "content": resp})
                st.rerun()

            if st.button("Lektion abschließen ✅"):
                data["completed_lessons"] += 1
                save_all_data(data)
                st.session_state.lesson_msgs = []
                st.balloons()
                st.rerun()

with tab_chat:
    st.markdown("<div class='main-card'>Übe frei ohne XP-Druck.</div>", unsafe_allow_html=True)
    # Hier kommt der normale Chat-Code von vorher rein (ohne XP-Update)
