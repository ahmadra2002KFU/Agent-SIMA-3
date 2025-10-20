import streamlit as st

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "👋 Hello, I'm your analytics assistant. You can ask me questions or attach a CSV/Excel file for analysis!"})

user_input = st.chat_input(
    "Say something and/or attach a data sheet (csv, excel file)",
    accept_file=True,
    file_type=["csv", "xlsx"],
)

if user_input:
    if user_input.files is not None and len(user_input.files) > 0:
        # Save the uploaded file to session_state for later use
        st.session_state['uploaded_file'] = user_input.files[0]
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"📁 File '{user_input.files[0].name}' received! I'll be able to analyze and answer questions about your data."
        })
    if user_input.text:
        st.session_state.messages.append({"role": "user", "content": user_input.text})
        

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


