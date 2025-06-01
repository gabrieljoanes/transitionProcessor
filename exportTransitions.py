import requests
import docx
import io
import random
import openai
import re
import json
from collections import Counter
from extract_few_shots import extract_few_shot_examples


def run_app(st):
    # --- CONFIG ---
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    def is_transition(phrase, use_gpt, model_choice):
        if not use_gpt:
            return True

        prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?
Phrase: \"{phrase}\"
Respond only with \"Yes\" or \"No\"."""

        response = client.chat.completions.create(
            model=model_choice,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip().lower() == "yes"

    def looks_like_date_or_invalid_code(phrase):
        if re.match(r"du\s\d{2}/?$", phrase, re.IGNORECASE):
            return True
        if phrase.lower().startswith("du ") and "/" in phrase:
            return True
        return False

    def normalize_strict(phrase):
        return re.sub(r'\s+', ' ', phrase.strip())

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

    # --- Streamlit UI ---
    st.title("🪄 Transition Extractor & Validator")
    st.write("Upload a `.docx` file. Then select options below and click **Start Processing** to extract and validate transitions.")

    uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])
    percent = st.selectbox("🔢 Percentage of transitions to validate:", [10, 30, 50, 75, 100], index=4)
    use_gpt = st.checkbox("✅ Use GPT to validate transitions", value=True)

    model_choice = None
    if use_gpt:
        model_choice = st.radio("🤖 Choose GPT model:", ["gpt-3.5-turbo", "gpt-4"], horizontal=True)

    if uploaded_file:
        if st.button("🚀 Start Processing"):
            with st.spinner("🔍 Extracting and validating transitions..."):
                try:
                    raw_candidates = extract_transitions_from_docx(uploaded_file.read())

                    candidates = []
                    for line in raw_candidates:
                        phrase = line.strip("•–-1234567890. ").strip()
                        if 2 <= len(phrase.split()) <= 7 and not looks_like_date_or_invalid_code(phrase):
                            candidates.append(phrase)

                    normalized_candidates = [normalize_strict(p) for p in candidates]
                    counter = Counter(normalized_candidates)
                    duplicates = [f"{p} ({count}x)" for p, count in counter.items() if count > 1]

                    seen = set()
                    unique_candidates = []
                    for original, norm in zip(candidates, normalized_candidates):
                        if norm not in seen:
                            seen.add(norm)
                            unique_candidates.append(original)

                    sample_size = max(1, int(len(unique_candidates) * percent / 100))
                    sampled_candidates = random.sample(unique_candidates, sample_size)

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

        if st.button("✨ Generate Few-Shot Examples"):
            with st.spinner("⚙️ Extracting few-shot examples..."):
                try:
                    path = "/tmp/temp_few_shot.docx"
                    with open(path, "wb") as f:
                        f.write(uploaded_file.read())

                    examples = extract_few_shot_examples(path)
                    st.success(f"{len(examples)} few-shot examples generated.")
                    st.json(examples[:3])
                    st.download_button(
                        label="📄 Download Few-Shot Examples (JSON)",
                        data=json.dumps(examples, ensure_ascii=False, indent=2),
                        file_name="few_shot_examples.json",
                        mime="application/json"
                    )
                except Exception as e:
                    st.error(f"❌ Error while generating few-shot examples: {e}")
