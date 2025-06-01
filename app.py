import streamlit as st
import random
import json
import os
from collections import Counter
from extract_utils import extract_transitions_from_docx, clean_and_filter_transitions, normalize_strict
from validator_utils import is_transition
from extract_fewshots import extract_few_shot_examples

# --- Streamlit Config ---
st.set_page_config(page_title="🪄 Transition Processor", layout="centered")
st.title("🪄 Transition Processor")

st.write("""
Upload a `.docx` file and choose your processing type.
This app supports transition extraction with optional GPT validation, as well as few-shot training example export.
""")

# --- File Upload ---
uploaded_file = st.file_uploader("📄 Upload a Word (.docx) file", type=["docx"])

# --- Options ---
output_format = st.selectbox("📦 Select output format:", ["Transitions TXT", "Few-shot JSON"])
percent = st.selectbox("🔢 Percentage of transitions to validate (only for Transitions TXT):", [10, 30, 50, 75, 100], index=4)
use_gpt = st.checkbox("✅ Use GPT to validate transitions (only for Transitions TXT)", value=True)
model_choice = st.radio("🤖 Choose GPT model:", ["gpt-3.5-turbo", "gpt-4"], horizontal=True) if use_gpt else None

# --- Start Processing ---
if uploaded_file and st.button("🚀 Start Processing"):
    with st.spinner("Processing file..."):
        try:
            if output_format == "Transitions TXT":
                raw_lines = extract_transitions_from_docx(uploaded_file.read())
                candidates = clean_and_filter_transitions(raw_lines)

                normalized = [normalize_strict(p) for p in candidates]
                counter = Counter(normalized)
                duplicates = [f"{p} ({count}x)" for p, count in counter.items() if count > 1]

                seen = set()
                unique_candidates = []
                for original, norm in zip(candidates, normalized):
                    if norm not in seen:
                        seen.add(norm)
                        unique_candidates.append(original)

                sample_size = max(1, int(len(unique_candidates) * percent / 100))
                sampled = random.sample(unique_candidates, sample_size)

                validated = [s for s in sampled if is_transition(s, use_gpt, model_choice)]

                if validated:
                    st.success(f"{len(validated)} transitions validated.")
                    st.code("\n".join(validated[:10]), language="text")

                    st.download_button(
                        "📥 Download Validated Transitions (txt)",
                        data="\n".join(validated),
                        file_name="validated_transitions.txt",
                        mime="text/plain"
                    )
                    if duplicates:
                        st.download_button(
                            "📤 Download Duplicates",
                            data="\n".join(duplicates),
                            file_name="duplicate_transitions.txt",
                            mime="text/plain"
                        )
                else:
                    st.warning("No valid transitions found.")

            elif output_format == "Few-shot JSON":
                with open("temp.docx", "wb") as f:
                    f.write(uploaded_file.read())
                examples = extract_few_shot_examples("temp.docx")
                fewshot_json = json.dumps(examples, ensure_ascii=False, indent=2)

                st.success(f"✅ Extracted {len(examples)} few-shot examples.")
                st.code(fewshot_json[:1000] + "..." if len(fewshot_json) > 1000 else fewshot_json, language="json")

                st.download_button(
                    label="📥 Download Few-shot JSON",
                    data=fewshot_json,
                    file_name="fewshot_examples.json",
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"❌ Error: {e}")
