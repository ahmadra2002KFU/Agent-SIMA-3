import streamlit as st
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
from metadata_extractor import MetadataExtractor
import pandas as pd
from llm_client import LLMClient
from openai import OpenAI

client = LLMClient()
# client = OpenAI(
#     api_key="empty",
#     base_url="http://localhost:8000/v1"
# )
# # print(client.models.list().data)
# model_id = client.models.list().data[0].id

st.title("Analytics Assistant")


if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "👋 Hello, I'm your analytics assistant. You can ask me questions or attach a CSV/Excel file for analysis!"})

# Initialize rules text if needed
if "user_rules" not in st.session_state:
    st.session_state["user_rules"] = []
    
if "file_data" in st.session_state:
    if "metadata_extractor" not in st.session_state:
        st.session_state['metadata'] = MetadataExtractor(filepath=st.session_state['uploaded_file']['upload_url'], filename=st.session_state['uploaded_file']['name'])

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], pd.DataFrame):
            st.dataframe(msg["content"])
        else:
            st.markdown(msg["content"])

user_input = st.chat_input(
    "Say something and/or attach a data sheet (csv, excel file)",
    accept_file=True,
    file_type=["csv", "xlsx"],
)

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

def add_rule(new_rule):
    if new_rule.strip() not in st.session_state["user_rules"]:
        st.session_state["user_rules"].append(new_rule.strip())
        st.session_state["rule_input_box"] = ""

with st.sidebar:
    st.markdown("### User LLM Rules (Optional)")
    # Use a text_input for each rule addition
    new_rule = st.text_input(
        "Add Rule",
        "",
        placeholder="Type a rule and press Enter...",
        key="rule_input_box", 
        on_change=lambda: add_rule(st.session_state["rule_input_box"])
    )

    # Process deletions and parsing
    if st.session_state["user_rules"]:
        with st.container():
            st.markdown("#### Saved Rules")
            to_delete = None  # Track which rule to delete
            for idx, rule in enumerate(st.session_state["user_rules"]):
                cols = st.columns([2,2])
                with cols[0]:
                    st.markdown(f"- {rule}")
                with cols[1]:
                    if st.button("Delete", key=f"delete_rule_{idx}"):
                        to_delete = idx
                        # print(to_delete)
            if to_delete is not None:
                print("Deleting rule: ", to_delete)
                st.session_state["user_rules"].pop(to_delete)
                st.rerun()

if user_input:
    if user_input.files is not None and len(user_input.files) > 0:
        # Save the uploaded file to session_state for later use
        st.session_state['uploaded_file'] = user_input.files[0]
        st.info(f"📁 File '{user_input.files[0].name}' received! I'll be able to analyze and answer questions about your data.")
        st.session_state['uploaded_file'] = user_input.files[0]
        st.session_state['metadata'] = MetadataExtractor(st.session_state['uploaded_file'])

    if user_input.text:
        st.session_state.messages.append({"role": "user", "content": user_input.text})
        st.chat_message("user").write(user_input.text)
        stream = client.chat.completions.create(
            model=model_id,
            messages=st.session_state.messages,
            stream=True
        )
        with st.chat_message("assistant"):
            client.generate_structured_response(
                user_message=user_input.text,
                system_prompt=SYSTEM_PROMPT,
                file_metadata=st.session_state['metadata'],
                user_rules=st.session_state['user_rules'],
                initial_response_temp=0.7,
                generated_code_temp=0.3,
                result_commentary_temp=0.2
            )
            msg = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": msg})




