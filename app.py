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

st.write("Upload a .docx file with real or mock paragraph pairs and transitions to extract clean few-shot training data.")

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
        st.error(f"❌ Error while generating few-shot examples: {e}") ... and the app.py developped previously for the transitions only output import streamlit as st
import requests
import docx
import io
import random
import openai
import re
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

# --- Helper: Filter out known non-transition patterns ---
def looks_like_date_or_invalid_code(phrase):
    if re.match(r"du\s\d{2}/?$", phrase, re.IGNORECASE):
        return True
    if phrase.lower().startswith("du ") and "/" in phrase:
        return True
    return False

# --- Helper: Normalize for strict deduplication ---
def normalize_strict(phrase):
    return re.sub(r'\s+', ' ', phrase.strip())

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

st.write("Upload a .docx file. Then select options below and click **Start Processing** to extract and validate transitions.")

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

                # Clean formatting and filter out invalid entries
                candidates = []
                for line in raw_candidates:
                    phrase = line.strip("•–-1234567890. ").strip()
                    if 2 <= len(phrase.split()) <= 7 and not looks_like_date_or_invalid_code(phrase):
                        candidates.append(phrase)

                # Normalize and find duplicates from the full cleaned list
                normalized_candidates = [normalize_strict(p) for p in candidates]
                counter = Counter(normalized_candidates)
                duplicates = [f"{p} ({count}x)" for p, count in counter.items() if count > 1]

                # Remove duplicates while preserving first occurrence
                seen = set()
                unique_candidates = []
                for original, norm in zip(candidates, normalized_candidates):
                    if norm not in seen:
                        seen.add(norm)
                        unique_candidates.append(original)

                # Sample from unique set
                sample_size = max(1, int(len(unique_candidates) * percent / 100))
                sampled_candidates = random.sample(unique_candidates, sample_size)

                # Validate
                validated = [phrase for phrase in sampled_candidates if is_transition(phrase, use_gpt, model_choice)]

                if validated:
                    st.success(f"{len(validated)} unique transitions validated out of {sample_size} processed.")
                    st.code("\n".join(validated[:10]), language="text")

                    st.download_button(
                        label="📥 Download All Unique Validated Transitions",
                        data="\n".join(validated),
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


