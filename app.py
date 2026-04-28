import streamlit as st
from ai_manager import get_spanish_tutor_response
from data_manager import load_vocab, add_duolingo_words

st.title("🇪🇸 HolaBot: Dein Spanisch-Lehrer")

# Initialisiere Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar: Wörter verwalten
st.sidebar.header("Wortschatz")
if st.sidebar.button("Duolingo Wörter importieren"):
    # Beispiel: hier könnte ein File-Uploader stehen
    dummy_data = ["hola", "como", "esta", "gracias"]
    add_duolingo_words(dummy_data)
    st.sidebar.success("Importiert!")

known_words = load_vocab()["known_words"]

# Chat anzeigen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Escribe algo en español..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # KI Antwort
    with st.chat_message("assistant"):
        response = get_spanish_tutor_response(prompt, known_words)
        st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})