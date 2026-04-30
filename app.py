import streamlit as st
import time
from data_manager import (load_user_data, save_user_data, check_daily_streak, 
                          update_progress, handle_wrong_answer, refill_hearts, buy_premium)
from ai_manager import generate_lesson_exercise, text_to_speech

# --- CONFIG & CSS ---
st.set_page_config(page_title="LingoApp Clone", page_icon="🦉", layout="centered")

st.markdown("""
<style>
    .top-bar {
        display: flex; justify-content: space-between; align-items: center;
        background-color: white; padding: 10px 20px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 30px; font-weight: bold;
    }
    .stat-item { display: flex; align-items: center; gap: 5px; font-size: 1.1rem; }
    .heart-icon { color: #ff4b4b; }
    .gem-icon { color: #1cb0f6; }
    .streak-icon { color: #ff9600; }
    
    /* Lernpfad Design */
    .path-container { display: flex; flex-direction: column; align-items: center; margin-top: 20px; }
    .path-node {
        width: 80px; height: 80px; border-radius: 50%; display: flex; 
        align-items: center; justify-content: center; font-size: 24px; font-weight: bold;
        color: white; cursor: pointer; border: 5px solid rgba(255,255,255,0.5);
        box-shadow: 0 6px 0 rgba(0,0,0,0.1); margin: 15px 0; z-index: 2; position: relative;
    }
    .node-done { background-color: #58cc02; box-shadow: 0 6px 0 #46a302; }
    .node-active { background-color: #ce82ff; box-shadow: 0 6px 0 #a561d1; transform: scale(1.1); }
    .node-locked { background-color: #e5e5e5; color: #afafaf; box-shadow: 0 6px 0 #cecece; }
    .path-line { width: 10px; height: 50px; background-color: #e5e5e5; margin: -20px 0; z-index: 1; }
    .line-done { background-color: #58cc02; }
    
    .stButton>button { width: 100%; border-radius: 15px; font-weight: bold; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- STATE INITIALIZATION ---
if "user_data" not in st.session_state:
    raw_data = load_user_data()
    st.session_state.user_data = check_daily_streak(raw_data)
if "active_lesson" not in st.session_state:
    st.session_state.active_lesson = None
if "current_exercise" not in st.session_state:
    st.session_state.current_exercise = None

data = st.session_state.user_data
hearts_display = "♾️" if data["premium"] else str(data["hearts"])

# --- TOP STATUS BAR ---
st.markdown(f"""
<div class="top-bar">
    <div class="stat-item"><span style="font-size: 1.5rem;">🇪🇸</span> Spanisch</div>
    <div class="stat-item streak-icon">🔥 {data['streak']}</div>
    <div class="stat-item gem-icon">💎 {data['gems']}</div>
    <div class="stat-item heart-icon">❤️ {hearts_display}</div>
</div>
""", unsafe_allow_html=True)

# --- TABS (Home, Shop, Profil) ---
tab_home, tab_shop, tab_profile = st.tabs(["🏠 Lernpfad", "🛒 Shop", "🛡️ Profil"])

with tab_home:
    if st.session_state.active_lesson is None:
        st.subheader(f"Unit {data['current_unit']}: Spanisch Basics")
        
        # Zeichne den Lernpfad (5 Knoten pro Unit)
        st.markdown('<div class="path-container">', unsafe_allow_html=True)
        for i in range(1, 6):
            # Bestimme den Status des Knotens
            if i < data["current_lesson"]:
                state_class = "node-done"
                icon = "⭐"
                is_disabled = True
            elif i == data["current_lesson"]:
                state_class = "node-active"
                icon = "🚀"
                is_disabled = False
            else:
                state_class = "node-locked"
                icon = "🔒"
                is_disabled = True
            
            # Button Rendern (versteckter Streamlit Button über dem CSS)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown(f'<div class="path-node {state_class}">{icon}</div>', unsafe_allow_html=True)
                if not is_disabled:
                    if st.button(f"Lektion {i} Starten", use_container_width=True):
                        if data["hearts"] > 0 or data["premium"]:
                            st.session_state.active_lesson = i
                            st.rerun()
                        else:
                            st.error("Du hast keine Herzen mehr! Gehe in den Shop.")
            
            # Pfad-Linie zeichnen (außer beim letzten Element)
            if i < 5:
                line_class = "line-done" if i < data["current_lesson"] else ""
                st.markdown(f'<div class="path-line {line_class}"></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # --- AKTIVE LEKTION ---
        st.header(f"Lektion {st.session_state.active_lesson}")
        
        if st.session_state.current_exercise is None:
            with st.spinner("KI generiert Übung..."):
                st.session_state.current_exercise = generate_lesson_exercise(
                    data["current_unit"], 
                    st.session_state.active_lesson, 
                    data["known_words"]
                )
                
        exercise = st.session_state.current_exercise
        st.info(exercise.get("question", "Übersetze diesen Satz:"))
        
        # Audio Button
        if "spanish_text" in exercise:
            audio_file = text_to_speech(exercise["spanish_text"])
            if audio_file:
                st.audio(audio_file)
        
        user_answer = st.text_input("Deine Antwort:", key="user_ans")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Antwort Prüfen", type="primary"):
                if not user_answer:
                    st.warning("Bitte gib eine Antwort ein.")
                else:
                    correct = str(exercise.get("correct_answer", "")).strip().lower()
                    if user_answer.strip().lower() == correct:
                        st.success("🎉 Richtig! +15 XP")
                        st.session_state.user_data = update_progress(data, 15, st.session_state.active_lesson)
                        st.session_state.active_lesson = None
                        st.session_state.current_exercise = None
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"Falsch! Die richtige Antwort war: **{exercise.get('correct_answer')}**")
                        st.session_state.user_data = handle_wrong_answer(data)
                        if st.session_state.user_data["hearts"] <= 0 and not data["premium"]:
                            st.warning("💔 Keine Herzen mehr! Lektion abgebrochen.")
                            st.session_state.active_lesson = None
                            st.session_state.current_exercise = None
                            time.sleep(2)
                            st.rerun()
        with col2:
            if st.button("Abbrechen"):
                st.session_state.active_lesson = None
                st.session_state.current_exercise = None
                st.rerun()

with tab_shop:
    st.header("🛒 Lingo-Shop")
    st.write("Gib deine hart verdienten Gems aus!")
    
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("### ❤️ Herzen auffüllen")
        st.write("Kosten: 350 Gems")
        if st.button("Kaufen (350)", key="buy_hearts"):
            if refill_hearts(data, 350):
                st.success("Herzen komplett aufgefüllt!")
                st.rerun()
            else:
                st.error("Nicht genug Gems oder Herzen sind bereits voll.")
                
    with sc2:
        st.markdown("### 🌟 Super Lingo")
        st.write("Unbegrenzte Herzen für immer!")
        st.write("Kosten: 1000 Gems")
        if data["premium"]:
            st.success("Bereits freigeschaltet!")
        else:
            if st.button("Aktivieren (1000)", key="buy_super"):
                if buy_premium(data, 1000):
                    st.balloons()
                    st.success("Super Lingo aktiviert!")
                    st.rerun()
                else:
                    st.error("Nicht genug Gems!")

with tab_profile:
    st.header("🛡️ Dein Profil")
    st.metric("Gesammelte XP", data["xp"])
    st.metric("Aktueller Streak", f"{data['streak']} Tage")
    st.metric("Premium Status", "Aktiv" if data["premium"] else "Inaktiv")
    st.write("### Bekannte Wörter")
    st.write(", ".join(data["known_words"]))
