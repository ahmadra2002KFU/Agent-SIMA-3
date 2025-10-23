
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
from metadata_extractor import MetadataExtractor
import pandas as pd
from llm_client import LLMClient
from openai import OpenAI
from chat_helper import display_assistant_message, display_user_message, add_rule
import streamlit as st

llm_client = LLMClient()

st.title("Analytics Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "👋 Hello, I'm your analytics assistant. You can ask me questions or attach a CSV/Excel file for analysis!"})

# Initialize rules text if needed
if "user_rules" not in st.session_state:
    st.session_state["user_rules"] = []
    
if "file_data" in st.session_state:
    if "metadata" not in st.session_state:
        st.session_state['metadata'] = MetadataExtractor(st.session_state['uploaded_file']).extract_metadata()

for msg in st.session_state.messages:
    display_assistant_message(msg) if msg["role"] == "assistant" else display_user_message(msg)

user_input = st.chat_input(
    "Say something and/or attach a data sheet (csv, excel file)",
    accept_file=True,
    file_type=["csv", "xlsx"],
)

if "metadata" in st.session_state:
    with st.sidebar:
        if "basic_info" in st.session_state:
            info = st.session_state['basic_info']
            st.markdown("### 📊 File Info")
            st.markdown(
                f"""
                **Filename:** `{info.get('filename', 'N/A')}`  
                **Rows:** {info.get('rows', 'N/A'):,}  
                **Columns:** {info.get('columns', 'N/A'):,}  
                **Memory Usage:** {info.get('memory_usage_mb', 'N/A')} MB  
                """
            )

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
            if to_delete is not None:
                st.session_state["user_rules"].pop(to_delete)
                st.rerun()

if user_input:
    if user_input.files is not None and len(user_input.files) > 0:
        # Save the uploaded file to session_state for later use
        st.session_state['uploaded_file'] = user_input.files[0]
        st.info(f"📁 File '{user_input.files[0].name}' received! I'll be able to analyze and answer questions about your data.")
        st.session_state['uploaded_file'] = user_input.files[0]
        metadata_extractor = MetadataExtractor(st.session_state['uploaded_file'])
        st.session_state['metadata'] = metadata_extractor.extract_metadata()
        st.session_state['basic_info'] = metadata_extractor.get_basic_info()

    if user_input.text:
        st.session_state.messages.append({"role": "user", "content": user_input.text})
        st.chat_message("user").write(user_input.text)
        SYSTEM_PROMPT="""You are an expert data analyst. Interpret code execution results by answering the user's ORIGINAL QUERY first, using the primary result in the correct context.

CRITICAL COMMENTARY STRUCTURE:
1. **ANSWER THE ORIGINAL QUERY**: Use the primary result to directly answer what the user asked
2. **METHODOLOGY EXPLANATION**: Explain how the code achieved this result
3. **TECHNICAL DETAILS**: Reference specific functions, operations, or techniques used
4. **CONTEXTUAL INSIGHTS**: Provide relevant additional insights

EXAMPLE for "What is the average age of American patients?":
"The average age of American patients is 54.8 years. The code calculated this by filtering for patients with 'American' nationality and using a custom age calculation function that computed age at admission by comparing Date_of_Birth with Admission_Date, accounting for whether the birthday had occurred yet in the admission year."

CRITICAL: The primary result must be interpreted in the context of the original user query. If the user asks for "average age", the result represents age in years, not a percentage or count."""

        with st.chat_message("assistant"):
            stream = llm_client.generate_structured_response(
                user_message=user_input.text,
                system_prompt=SYSTEM_PROMPT,
                file_metadata=st.session_state['metadata'],
                user_rules=st.session_state['user_rules'],
                initial_response_temp=0.7,
                generated_code_temp=0.3,
                result_commentary_temp=0.2
            )
            response = []   
            for msg in st.write_stream(stream):
                response.append(msg)
                display_assistant_message(msg)
            st.session_state.messages.append({"role": "assistant", "content": response})




