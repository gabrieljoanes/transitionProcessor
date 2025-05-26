import streamlit as st
import requests
import docx
import io
import openai

# --- CONFIG ---
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- Helper: Check if a string is a transition ---
def is_transition(phrase):
    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?
Phrase: "{phrase}"
Respond only with "Yes" or "No"."""
    
    response = openai.ChatCompletion.create(
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

# --- UI ---
st.title("🪄 Transition Extractor & Validator")
st.write("This app downloads a Word document, extracts transition phrases after the `Transitions:` label, and filters them using AI.")

# --- Input: Public link to DOCX ---
doc_url = st.text_input("📎 Paste public DOCX URL", "")

if st.button("🔍 Extract Transitions"):
    if not doc_url:
        st.error("Please enter a valid public DOCX URL.")
    else:
        with st.spinner("Downloading and extracting..."):
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(doc_url, headers=headers)

            if r.status_code != 200:
                st.error(f"Download failed (status {r.status_code})")
            else:
                raw_candidates = extract_transitions_from_docx(r.content)
                cleaned = []
                for line in raw_candidates:
                    phrase = line.strip("•–-1234567890. ").strip()
                    if 2 <= len(phrase.split()) <= 7 and is_transition(phrase):
                        cleaned.append(phrase)

                if cleaned:
                    st.success(f"{len(cleaned)} validated transitions found.")
                    st.write("📋 Sample Output:")
                    st.code("\n".join(cleaned[:10]), language="text")

                    # Download option
                    st.download_button(
                        label="📥 Download All Transitions",
                        data="\n".join(cleaned),
                        file_name="validated_transitions.txt",
                        mime="text/plain"
                    )
                else:
                    st.warning("No valid transitions found.")
