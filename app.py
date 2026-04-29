import streamlit as st
from ai_manager import get_spanish_tutor_response
from data_manager import load_vocab, add_duolingo_words

# Bonus Feature: Bessere Seitendarstellung
st.set_page_config(page_title="HolaBot", page_icon="🇪🇸", layout="centered")

st.title("🇪🇸 HolaBot: Dein KI-Spanisch-Lehrer")
st.write("¡Hola! Schreib mir etwas auf Spanisch und wir üben zusammen.")

# Initialisiere den Chatverlauf im Speicher
if "messages" not in st.session_state:
   st.session_state.messages = []

# --- SIDEBAR (Bonus Features) ---
with st.sidebar:
   st.header("⚙️ Einstellungen")
   if st.button("🗑️ Chatverlauf löschen"):
       st.session_state.messages = []
       st.rerun()

   st.divider()

   st.header("📚 Dein Wortschatz")
   st.write("Trage hier Wörter ein, die du bereits kennst.")
   new_word = st.text_input("Neues Wort (z.B. el perro):")
   if st.button("➕ Hinzufügen") and new_word:
       add_duolingo_words([new_word.strip()])
       st.success(f"'{new_word}' wurde gespeichert!")

   vocab_data = load_vocab()
   with st.expander("Alle gelernten Wörter ansehen"):
       if vocab_data.get("known_words"):
           st.write(", ".join(vocab_data["known_words"]))
       else:
           st.write("Noch keine Wörter gespeichert.")

# --- CHAT BEREICH ---
# Zeige alte Nachrichten an
for message in st.session_state.messages:
   with st.chat_message(message["role"]):
       st.markdown(message["content"])

# Eingabefeld für den Nutzer
if prompt := st.chat_input("Escribe algo en español..."):
   # Nachricht des Nutzers anzeigen und speichern
   st.session_state.messages.append({"role": "user", "content": prompt})
   with st.chat_message("user"):
       st.markdown(prompt)

   # KI-Antwort generieren
   with st.chat_message("assistant"):
       # Bonus Feature: Lade-Animation
       with st.spinner("HolaBot überlegt..."):
           known_words = load_vocab()
           response = get_spanish_tutor_response(prompt, known_words)
           st.markdown(response)

   # Antwort speichern
   st.session_state.messages.append({"role": "assistant", "content": response})
