import streamlit as st
from extract_utils import extract_transitions_from_docx, clean_and_filter_transitions, normalize_strict
from extract_fewshots import extract_few_shot_examples_and_jsonl
import json

st.set_page_config(page_title="Transition Processor", page_icon="🧠")
st.title("🧠 Transition Processor")

st.write("Upload a `.docx` file and choose the desired output format.")

# --- Upload File ---
uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

# --- Output Format ---
output_format = st.selectbox(
    "📦 Select export format:",
    ["Transitions TXT", "Few-shots / Fine-tuning JSONL"]
)

# --- Start Processing ---
if uploaded_file and st.button("🚀 Start Processing"):
    with st.spinner("Processing..."):

        if output_format == "Transitions TXT":
            try:
                raw_candidates = extract_transitions_from_docx(uploaded_file.read())
                candidates = clean_and_filter_transitions(raw_candidates)
                normalized = [normalize_strict(c) for c in candidates]
                unique = list(dict.fromkeys(normalized))  # Preserve order, deduplicate

                st.success(f"✅ {len(unique)} unique transitions extracted.")
                st.code("\n".join(unique[:10]), language="text")

                st.download_button(
                    label="📥 Download Transitions TXT",
                    data="\n".join(unique),
                    file_name="transitions.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"❌ Error: {e}")

        elif output_format == "Few-shots / Fine-tuning JSONL":
            try:
                # Save file temporarily
                with open("temp.docx", "wb") as f:
                    f.write(uploaded_file.read())

                fewshots_json, fine_tune_jsonl = extract_few_shot_examples_and_jsonl("temp.docx")

                st.success("✅ Few-shot and fine-tuning files generated.")

                st.download_button(
                    label="📥 Download Few-shot JSON",
                    data=fewshots_json,
                    file_name="fewshot_examples.json",
                    mime="application/json"
                )

                st.download_button(
                    label="📥 Download Fine-tuning JSONL",
                    data=fine_tune_jsonl,
                    file_name="fine_tuning_data.jsonl",
                    mime="application/jsonl"
                )

            except Exception as e:
                st.error(f"❌ Error during extraction: {e}")
