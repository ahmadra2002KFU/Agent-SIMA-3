import streamlit as st
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
from metadata_extractor import MetadataExtractor
import pandas as pd


# TODO: delete uploaded files when session expires.

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "👋 Hello, I'm your analytics assistant. You can ask me questions or attach a CSV/Excel file for analysis!"})


if "file_data" in st.session_state:
    if "metadata_extractor" not in st.session_state:
        st.session_state['metadata'] = MetadataExtractor(filepath=st.session_state['uploaded_file']['upload_url'], filename=st.session_state['uploaded_file']['name'])

user_input = st.chat_input(
    "Say something and/or attach a data sheet (csv, excel file)",
    accept_file=True,
    file_type=["csv", "xlsx"],
)


st.title("Analytics Assistant")

if "metadata" in st.session_state:
    with st.sidebar:
        info = st.session_state['metadata'].get_basic_info()
        st.markdown("### 📊 File Info")
        st.markdown(
            f"""
            **Filename:** `{info.get('filename', 'N/A')}`  
            **Rows:** {info.get('rows', 'N/A'):,}  
            **Columns:** {info.get('columns', 'N/A'):,}  
            **Memory Usage:** {info.get('memory_usage_mb', 'N/A')} MB  
            """
        )

if user_input:
    if user_input.files is not None and len(user_input.files) > 0:
        # Save the uploaded file to session_state for later use
        st.session_state['uploaded_file'] = user_input.files[0]
        st.info(f"📁 File '{user_input.files[0].name}' received! I'll be able to analyze and answer questions about your data.")
        st.session_state['uploaded_file'] = user_input.files[0]
        st.session_state['metadata'] = MetadataExtractor(st.session_state['uploaded_file'])

    if user_input.text:
        st.session_state.messages.append({"role": "user", "content": user_input.text})
        

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], pd.DataFrame):
            st.dataframe(msg["content"])
        else:
            st.markdown(msg["content"])


