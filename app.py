import streamlit as st
import os
import json
from utils.extract_utils import extract_transitions_from_docx, extract_long_paragraph_after_marker, extract_transition_list
from validator_utils import build_fewshots_with_gpt
from datetime import datetime

# --- UI ---
st.set_page_config(page_title="Transition Extractor", layout="centered")
st.title("🪄 Transition Extractor & Validator")

uploaded_file = st.file_uploader("📄 Upload a Word (.docx) file", type=["docx"])

# --- Options ---
extract_only_transitions = st.checkbox("Extract transitions only (.txt file)", value=False)
use_gpt = st.checkbox("Use GPT for few-shot extraction", value=True)
fewshot_mode = st.checkbox("Enable few-shot generation", value=True)

if uploaded_file:
    bytes_data = uploaded_file.read()
    docx_text = bytes_data.decode("utf-8", errors="ignore")  # In case we use raw text somewhere

    # --- Option 1: Just extract transitions into a .txt file ---
    if extract_only_transitions:
        transitions = extract_transitions_from_docx(bytes_data)
        transition_txt = "\n".join(transitions)

        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "transitions.txt")
        with open(desktop_path, "w", encoding="utf-8") as f:
            f.write(transition_txt)

        st.success(f"✅ Transitions saved to: {desktop_path}")

    # --- Option 2: Build few-shot examples using GPT ---
    elif use_gpt and fewshot_mode:
        transitions = extract_transition_list(docx_text)
        long_para = extract_long_paragraph_after_marker(docx_text)

        model_choice = st.radio("🤖 Choose GPT model:", ["gpt-3.5-turbo", "gpt-4"], horizontal=True)

        fewshots = build_fewshots_with_gpt(long_para, transitions, model_choice=model_choice)

        if fewshots:
            st.subheader("✅ GPT-generated Few-shot Examples")
            for fs in fewshots:
                st.json(fs)

            # Save to file on Desktop with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fewshots_{timestamp}.json"
            filepath = os.path.join(os.path.expanduser("~"), "Desktop", filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(fewshots, f, ensure_ascii=False, indent=2)

            st.success(f"✅ Few-shot examples saved to: {filepath}")
        else:
            st.warning("⚠️ No valid few-shot examples were generated.")
