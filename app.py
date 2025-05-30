import streamlit as st
import requests
import docx
import io
import random
import openai

# --- CONFIG ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Helper: Check if a string is a transition ---
def is_transition(phrase, use_gpt, model_choice):
    if not use_gpt:
        return True  # Assume all are valid if GPT is skipped

    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?
Phrase: "{phrase}"
Respond only with "Yes" or "No"."""

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

st.write("Upload a `.docx` Word document. This tool extracts transition phrases listed after `Transitions:` and optionally uses GPT to validate them.")

# Upload file
uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

# Sampling percentage
percent = st.selectbox("🔢 Percentage of transitions to process:", [10, 30, 50, 75, 100], index=4)

# Validation toggle
use_gpt = st.checkbox("✅ Use GPT to validate transitions", value=True)

# Model choice (only shown if GPT is used)
model_choice = None
if use_gpt:
    model_choice = st.radio("🤖 Choose GPT model:", ["gpt-3.5-turbo", "gpt-4"], horizontal=True)

# Process file
if uploaded_file is not None:
    with st.spinner("🔍 Processing document..."):
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

            # Validate if needed
            cleaned = [phrase for phrase in sampled_candidates if is_transition(phrase, use_gpt, model_choice)]

            if cleaned:
                st.success(f"{len(cleaned)} validated transitions found out of {len(sampled_candidates)} processed.")
                st.write("📋 Sample of validated transitions:")
                st.code("\n".join(cleaned[:10]), language="text")

                st.download_button(
                    label="📥 Download All Transitions",
                    data="\n".join(cleaned),
                    file_name="validated_transitions.txt",
                    mime="text/plain"
                )
            else:
                st.warning("No valid transitions found in the file.")
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
