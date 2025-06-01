# --- FILE: app_extractor.py ---
import streamlit as st
import random
from collections import Counter
from extract_utils import extract_transitions_from_docx, looks_like_date_or_invalid_code, normalize_strict
from validator_utils import is_transition

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
