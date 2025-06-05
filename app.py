import streamlit as st
import docx
import io
import os
import json
from datetime import datetime
from utils.extract_utils import extract_transitions_from_docx, extract_long_paragraph_after_marker, extract_transition_list
from utils.summarizer import summarize_paragraph

# --- UI Setup ---
st.set_page_config(page_title="🪄 Transition Extractor", layout="centered")
st.title("🪄 Transition Extractor & Few-Shot Generator")

st.write("""
Upload a `.docx` file containing transitions.
Choose whether to extract transitions, generate few-shot examples, or both.
Optionally use GPT to summarize paragraphs in few-shots.
""")

# --- Upload File ---
uploaded_file = st.file_uploader("📄 Upload Word (.docx) file", type=["docx"])

if uploaded_file:
    bytes_data = uploaded_file.read()

    # --- Select processing options ---
    extract_only = st.checkbox("📄 Extract only transitions", value=False)
    do_fewshots = st.checkbox("✨ Generate few-shot examples", value=True)
    use_gpt = st.checkbox("🤖 Summarize A & B with GPT", value=False)
    model = st.radio("Model to use", ["gpt-3.5-turbo", "gpt-4"], horizontal=True) if use_gpt else None
    limit = st.slider("Limit number of few-shots", 1, 50, 10) if do_fewshots else None

    if st.button("🚀 Run Extraction"):
        st.success("Processing file...")

        if extract_only:
            transitions = extract_transitions_from_docx(bytes_data)
            filename = f"transitions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(transitions))
            st.success(f"✅ Transitions saved to: {path}")

        if do_fewshots:
            long_paragraph = extract_long_paragraph_after_marker(bytes_data)
            transition_list = extract_transition_list(bytes_data)

            results = []
            for i, transition in enumerate(transition_list):
                split_parts = long_paragraph.split(transition)
                if len(split_parts) < 2:
                    continue
                a = split_parts[0].strip().split(". ")[-2:]
                b = split_parts[1].strip().split(". ")[:2]
                paragraph_a = ". ".join(a).strip()
                paragraph_b = ". ".join(b).strip()

                if use_gpt:
                    paragraph_a = summarize_paragraph(paragraph_a, model)
                    paragraph_b = summarize_paragraph(paragraph_b, model)

                results.append({
                    "paragraph_a": paragraph_a,
                    "transition": transition.strip(),
                    "paragraph_b": paragraph_b
                })
                long_paragraph = split_parts[1]
                if limit and len(results) >= limit:
                    break

            json_filename = f"fewshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = os.path.join(os.path.expanduser("~"), "Desktop", json_filename)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            st.success(f"✅ Few-shots saved to: {output_path}")
