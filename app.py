import streamlit as st
import docx
import io
import json
import random
import re
from collections import Counter
import openai

# --- CONFIG ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Transition Extraction Utilities ---
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

def is_transition(phrase, use_gpt, model_choice):
    if not use_gpt:
        return True
    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?\nPhrase: \"{phrase}\"\nRespond only with \"Yes\" or \"No\"."""
    response = client.chat.completions.create(
        model=model_choice,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().lower() == "yes"

def looks_like_date_or_invalid_code(phrase):
    return re.match(r"du\\s\\d{2}/?$", phrase, re.IGNORECASE) or (phrase.lower().startswith("du ") and "/" in phrase)

def normalize_strict(phrase):
    return re.sub(r'\\s+', ' ', phrase.strip())

# --- Few-Shot Example Extraction ---
def extract_few_shot_examples(docx_path):
    doc = docx.Document(docx_path)
    examples = []
    paragraph_a = None
    transition = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text or text.lower().startswith("transitions"):
            continue
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

# --- Streamlit UI ---
st.title("📄 Transition Tool: Extractor or Few-Shot Generator")

uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

mode = st.radio("Choose mode:", ["🪄 Transition Extractor", "🧠 Few-Shot Generator"])

if uploaded_file:
    if mode == "🪄 Transition Extractor":
        percent = st.selectbox("🔢 Percentage of transitions to validate:", [10, 30, 50, 75, 100], index=4)
        use_gpt = st.checkbox("✅ Use GPT to validate transitions", value=True)
        model_choice = st.radio("🤖 Choose GPT model:", ["gpt-3.5-turbo", "gpt-4"], horizontal=True) if use_gpt else None

        if st.button("🚀 Start Transition Processing"):
            with st.spinner("🔍 Extracting and validating transitions..."):
                try:
                    raw_candidates = extract_transitions_from_docx(uploaded_file.read())
                    candidates = []
                    for line in raw_candidates:
                        phrase = line.strip("•–-1234567890. ").strip()
                        if 2 <= len(phrase.split()) <= 7 and not looks_like_date_or_invalid_code(phrase):
                            candidates.append(phrase)

                    normalized = [normalize_strict(p) for p in candidates]
                    counter = Counter(normalized)
                    duplicates = [f"{p} ({count}x)" for p, count in counter.items() if count > 1]

                    seen = set()
                    unique = []
                    for original, norm in zip(candidates, normalized):
                        if norm not in seen:
                            seen.add(norm)
                            unique.append(original)

                    sample_size = max(1, int(len(unique) * percent / 100))
                    sampled = random.sample(unique, sample_size)

                    validated = [p for p in sampled if is_transition(p, use_gpt, model_choice)]

                    st.success(f"{len(validated)} unique transitions validated out of {sample_size} processed.")
                    st.code("\n".join(validated[:10]), language="text")

                    st.download_button("📥 Download Validated Transitions", data="\n".join(validated), file_name="validated_transitions.txt")

                    if duplicates:
                        st.download_button("📤 Download Duplicates", data="\n".join(duplicates), file_name="duplicate_transitions.txt")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    elif mode == "🧠 Few-Shot Generator":
        if st.button("🚀 Generate Few-Shot Examples"):
            try:
                with open("/tmp/temp.docx", "wb") as f:
                    f.write(uploaded_file.read())

                few_shot_examples = extract_few_shot_examples("/tmp/temp.docx")

                transition_counts = Counter(ex["transition"] for ex in few_shot_examples)
                redundant = {t for t, count in transition_counts.items() if count > 1}
                filtered = [ex for ex in few_shot_examples if ex["transition"] not in redundant]
                removed_count = len(few_shot_examples) - len(filtered)

                few_shot_examples = filtered

                st.success(f"✅ {len(few_shot_examples)} few-shot examples generated.")
                st.write(f"🧹 Removed {removed_count} redundant examples.")
                st.json(few_shot_examples[:3], expanded=False)

                st.download_button(
                    label="📥 Download Few-Shot Examples",
                    data=json.dumps(few_shot_examples, ensure_ascii=False, indent=2),
                    file_name="clean_few_shot_examples.json",
                    mime="application/json"
                )
            except Exception as e:
                st.error(f"❌ Error while generating few-shot examples: {e}")
