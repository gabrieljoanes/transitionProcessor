import streamlit as st
import requests
import docx
import io
import openai

# --- CONFIG ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Helper: Check if a string is a transition ---
def is_transition(phrase):
    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?
Phrase: "{phrase}"
Respond only with "Yes" or "No"."""

    response = client.chat.completions.create(
        model="gpt-4",
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
st.write("Upload a `.docx` Word document. The app will extract transition phrases listed after the label `Transitions:` and use AI to check which ones are real transitions.")

# --- Upload File ---
uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

if uploaded_file is not None:
    with st.spinner("🔍 Processing document..."):
        try:
            raw_candidates = extract_transitions_from_docx(uploaded_file.read())

            cleaned = []
            for line in raw_candidates:
                phrase = line.strip("•–-1234567890. ").strip()
                if 2 <= len(phrase.split()) <= 7 and is_transition(phrase):
                    cleaned.append(phrase)

            if cleaned:
                st.success(f"{len(cleaned)} validated transitions found.")
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
