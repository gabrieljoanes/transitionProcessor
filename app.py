import streamlit as st
import requests
import docx
import io
import random
import openai
from collections import Counter

# --- CONFIG ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Helper: Check if a string is a transition ---
def is_transition(phrase, use_gpt, model_choice):
    if not use_gpt:
        return True  # Skip validation and treat all as valid

    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?
Phrase: \"{phrase}\"
Respond only with \"Yes\" or \"No\"."""

    response = client.chat.completions.create(
        model=model_choice,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip().lower() == "yes"

# --- Helper: Extract transitions from DOCX ---
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

# --- Streamlit Interface ---
st.title("🪄 Transition Extractor & Validator")

st.write("Upload a `.docx` file. Then select options below and click **Start Processing** to extract and validate transitions.")

# --- Upload File ---
uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

# --- Options ---
percent = st.selectbox("🔢 Percentage of transitions to validate:", [10, 30, 50, 75, 100], index=4)
use_gpt = st.checkbox("✅ Use GPT to validate transitions", value=True)

model_choice = None
if use_gpt:
    model_choice = st.radio("🤖 Choose GPT model:", ["gpt-3.5-turbo", "gpt-4"], horizontal=True)

# --- Processing Button ---
if uploaded_file:
    if st.button("🚀 Start Processing"):
        with st.spinner("🔍 Extracting and validating transitions..."):
            try:
                raw_candidates = extract_transitions_from_docx(uploaded_file.read())

                # Clean formatting
                candidates = [
                    line.strip("•–-1234567890. ").strip()
                    for line in raw_candidates
                    if 2 <= len(line.strip("•–-1234567890. ").strip().split()) <= 7
                ]

                # Sample
                sample_size = max(1, int(len(candidates) * percent / 100))
                sampled_candidates = random.sample(candidates, sample_size)

                # Validate
                validated = [phrase for phrase in sampled_candidates if is_transition(phrase, use_gpt, model_choice)]

                # Count duplicates
                counter = Counter(validated)
                duplicates = [f"{phrase} ({count}x)" for phrase, count in counter.items() if count > 1]

                # Remove repetitive transitions (keep only one instance per phrase)
                unique_cleaned = list(dict.fromkeys(validated))

                if unique_cleaned:
                    st.success(f"{len(unique_cleaned)} unique transitions validated out of {sample_size} processed.")
                    st.code("\n".join(unique_cleaned[:10]), language="text")

                    st.download_button(
                        label="📥 Download All Unique Validated Transitions",
                        data="\n".join(unique_cleaned),
                        file_name="validated_transitions.txt",
                        mime="text/plain"
                    )

                    if duplicates:
                        st.download_button(
                            label="📤 Download Duplicate Transitions for Review",
                            data="\n".join(duplicates),
                            file_name="duplicate_transitions.txt",
                            mime="text/plain"
                        )
                else:
                    st.warning("No valid transitions found.")
            except Exception as e:
                st.error(f"❌ Error: {e}")
