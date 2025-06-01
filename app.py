import streamlit as st
import random
import docx
import io
import re
from collections import Counter
from extract_utils import extract_transitions_from_docx, clean_and_filter_transitions, normalize_strict
from validator_utils import is_transition

# --- UI Configuration ---
st.set_page_config(page_title="🪄 Transition Extractor", layout="centered")
st.title("🪄 Transition Extractor & Validator")

st.write("""
Upload a `.docx` file and choose your options.
This app extracts potential transition phrases and optionally validates them using GPT.
""")

# --- File Upload ---
uploaded_file = st.file_uploader("📄 Upload a Word (.docx) file", type=["docx"])

# --- Options ---
percent = st.selectbox("🔢 Percentage of transitions to validate:", [10, 30, 50, 75, 100], index=4)
use_gpt = st.checkbox("✅ Use GPT to validate transitions", value=True)
model_choice = st.radio("🤖 Choose GPT model:", ["gpt-3.5-turbo", "gpt-4"], horizontal=True) if use_gpt else None

# --- Trigger Processing ---
if uploaded_file and st.button("🚀 Start Processing"):
    with st.spinner("🔍 Extracting and validating transitions..."):
        try:
            # Extract from DOCX
            raw_lines = extract_transitions_from_docx(uploaded_file.read())
            candidates = clean_and_filter_transitions(raw_lines)

            # Deduplicate strictly
            normalized = [normalize_strict(p) for p in candidates]
            counter = Counter(normalized)
            duplicates = [f"{p} ({count}x)" for p, count in counter.items() if count > 1]

            seen = set()
            unique_candidates = []
            for original, norm in zip(candidates, normalized):
                if norm not in seen:
                    seen.add(norm)
                    unique_candidates.append(original)

            # Sample subset
            sample_size = max(1, int(len(unique_candidates) * percent / 100))
            sampled = random.sample(unique_candidates, sample_size)

            # GPT Validation (optional)
            validated = [s for s in sampled if is_transition(s, use_gpt, model_choice)]

            if validated:
                st.success(f"{len(validated)} transitions validated.")
                st.code("\n".join(validated[:10]), language="text")

                st.download_button("📥 Download Validated Transitions (txt)", "\n".join(validated), "validated_transitions.txt")
                if duplicates:
                    st.download_button("📤 Download Duplicate Transitions", "\n".join(duplicates), "duplicate_transitions.txt")
            else:
                st.warning("No valid transitions found.")
        except Exception as e:
            st.error(f"❌ Error: {e}")
