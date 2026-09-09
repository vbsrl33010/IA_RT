import streamlit as st
import requests

st.set_page_config(page_title="Assistente Tecnico", page_icon="🤖", layout="centered")

st.title("Assistente Tecnico")
st.write("Inserisci qui sotto la richiesta o descrivi il problema per ottenere una risposta immediata.")

# Indirizzo del tuo backend Flask già attivo su Render
BACKEND_URL = "https://ia-rt.onrender.com/api/v1/chat"

# Gestione della cronologia dei messaggi nella sessione
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostra i messaggi passati
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Casella di input per l'utente in basso
if prompt := st.chat_input("Scrivi qui il problema o la domanda..."):
    # Salva e mostra il messaggio dell'utente
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Invia la richiesta al backend Flask su Render
    with st.chat_message("assistant"):
        with st.spinner("Elaborazione in corso..."):
            try:
                response = requests.post(BACKEND_URL, json={"message": prompt}, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    # Estrae la risposta in base a come è strutturato il JSON del tuo Flask
                    answer = data.get("response") or data.get("reply") or data.get("message") or str(data)
                else:
                    answer = f"Errore del server (Codice {response.status_code})."
            except Exception as e:
                answer = f"Impossibile connettersi al server: {e}"
            
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
