import streamlit as st
import docx
import io
import json
import re
from collections import Counter

# --- Helper: Extract transitions from DOCX for validation only ---
def extract_transitions_from_docx(docx_bytes):
    doc = docx.Document(io.BytesIO(docx_bytes))
    transitions_raw = []
    capture = False

    for para in doc.paragraphs:
        text = para.text.strip()
        if "transitions" in text.lower():
            capture = True
            continue
        if capture:
            if not text:
                break
            transitions_raw.append(text)
    return transitions_raw

# --- Few-shot extractor from DOCX ---
def extract_few_shot_examples(docx_path):
    doc = docx.Document(docx_path)
    examples = []
    paragraph_a = None
    transition = None

    for para in doc.paragraphs:
        text = para.text.strip()

        # Skip empty or transition header
        if not text or text.lower().startswith("transitions"):
            continue

        # Heuristic: Transition lines are often short and sentence-like
        if is_transition_line(text):
            transition = text
            continue

        if transition and paragraph_a:
            paragraph_b = text
            if transition not in paragraph_a and transition not in paragraph_b:
                examples.append({
                    "paragraph_a": paragraph_a,
                    "transition": transition,
                    "paragraph_b": paragraph_b
                })
            transition = None
            paragraph_a = paragraph_b
        else:
            paragraph_a = text

    return examples

def is_transition_line(text):
    return 2 <= len(text.split()) <= 10 and text.endswith((':', '.', '!', '?')) is False

# --- Streamlit App ---
st.title("🧠 Few-Shot Generator from Word File")

st.write("Upload a `.docx` file with real or mock paragraph pairs and transitions to extract clean few-shot training data.")

uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

if uploaded_file and st.button("🚀 Generate Few-Shot Examples"):
    try:
        # Save uploaded file to temp path
        with open("/tmp/temp.docx", "wb") as f:
            f.write(uploaded_file.read())

        few_shot_examples = extract_few_shot_examples("/tmp/temp.docx")

        # Count and remove redundant transitions
        transition_counts = Counter(ex["transition"] for ex in few_shot_examples)
        redundant_transitions = {t for t, count in transition_counts.items() if count > 1}
        filtered_examples = [
            ex for ex in few_shot_examples if ex["transition"] not in redundant_transitions
        ]
        removed_count = len(few_shot_examples) - len(filtered_examples)

        few_shot_examples = filtered_examples

        st.success(f"✅ {len(few_shot_examples)} few-shot examples generated.")
        st.write(f"🧹 Removed {removed_count} examples due to repeated transitions.")

        # Preview sample
        st.subheader("📋 Example Output")
        st.json(few_shot_examples[:3], expanded=False)

        # Download button
        st.download_button(
            label="📥 Download Clean Few-Shot Examples",
            data=json.dumps(few_shot_examples, ensure_ascii=False, indent=2),
            file_name="clean_few_shot_examples.json",
            mime="application/json"
        )

    except Exception as e:
        st.error(f"❌ Error while generating few-shot examples: {e}")
