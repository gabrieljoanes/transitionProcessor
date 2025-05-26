import streamlit as st
import requests
import docx
import io
import openai
import json

# --- CONFIG ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Check if phrase is a transition ---
def is_transition(phrase):
    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?
Phrase: "{phrase}"
Respond only with "Yes" or "No"."""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().lower() == "yes"

# --- Extract transitions from DOCX ---
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

# --- Few-shot JSON (optionally limited) ---
def build_few_shot_json(transitions, limit=None):
    few_shot = []
    subset = transitions[:limit] if limit else transitions
    for i, phrase in enumerate(subset):
        few_shot.append({
            "input": f"Exemple {i+1} avant la transition.\nTRANSITION\nExemple {i+1} après la transition.",
            "transition": phrase
        })
    return json.dumps(few_shot, ensure_ascii=False, indent=2)

# --- Fine-tuning JSONL (optionally limited) ---
def build_fine_tuning_jsonl(transitions, limit=None):
    lines = []
    subset = transitions[:limit] if limit else transitions
    for i, phrase in enumerate(subset):
        example = {
            "messages": [
                {"role": "user", "content": f"Paragraph A:\nExemple {i+1} avant la transition.\n\nParagraph B:\nExemple {i+1} après la transition."},
                {"role": "assistant", "content": phrase}
            ]
        }
        lines.append(json.dumps(example, ensure_ascii=False))
    return "\n".join(lines)

# --- Streamlit Interface ---
st.title("🪄 Transition Extractor & Validator")
st.write("Upload a `.docx` file with transitions. Choose sample or full mode below to control how many transitions are processed and exported.")

# --- Mode selection ---
sample_mode = st.toggle("⚙️ Limit to 10 transitions (sample mode)", value=True)
limit = 10 if sample_mode else None

# --- File upload ---
uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

if uploaded_file is not None:
    with st.spinner("🔍 Processing document..."):
        try:
            raw_candidates = extract_transitions_from_docx(uploaded_file.read())
            cleaned = []

            subset = raw_candidates[:limit] if limit else raw_candidates
            for line in subset:
                phrase = line.strip("•–-1234567890. ").strip()
                if 2 <= len(phrase.split()) <= 7 and is_transition(phrase):
                    cleaned.append(phrase)

            if cleaned:
                st.success(f"{len(cleaned)} validated transitions {'(limited to 10)' if sample_mode else '(full list)'}")
                st.write("📋 Preview of transitions:")
                st.code("\n".join(cleaned), language="text")

                # --- Downloads ---
                st.download_button(
                    label="📥 Download Transitions (.txt)",
                    data="\n".join(cleaned),
                    file_name="validated_transitions.txt",
                    mime="text/plain"
                )

                st.download_button(
                    label="📥 Download Few-Shot Format (.json)",
                    data=build_few_shot_json(cleaned, limit),
                    file_name="few_shot_transitions.json",
                    mime="application/json"
                )

                st.download_button(
                    label="📥 Download Fine-Tuning Format (.jsonl)",
                    data=build_fine_tuning_jsonl(cleaned, limit),
                    file_name="fine_tuning_transitions.jsonl",
                    mime="application/jsonl"
                )
            else:
                st.warning("No valid transitions found.")
        except Exception as e:
            st.error(f"❌ Error: {e}")
