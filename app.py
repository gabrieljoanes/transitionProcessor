import streamlit as st
import requests
import docx
import io
import openai
import json

# --- CONFIG ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Transition validator ---
def is_transition(phrase):
    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?
Phrase: "{phrase}"
Respond only with "Yes" or "No"."""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().lower() == "yes"

# --- Extract transitions + context from DOCX ---
def extract_transitions_with_context(docx_bytes):
    doc = docx.Document(io.BytesIO(docx_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    transitions = []
    i = 0
    while i < len(paragraphs):
        if "transitions" in paragraphs[i].lower():
            i += 1
            while i < len(paragraphs) and len(transitions) < 200:
                line = paragraphs[i].strip("•–-1234567890. ").strip()
                if not line or line.lower().startswith("à savoir"):
                    break
                if 2 <= len(line.split()) <= 7 and is_transition(line):
                    para_before = paragraphs[i - 2] if i >= 2 else "Paragraphe précédent manquant."
                    para_after = paragraphs[i - 1] if i >= 1 else "Paragraphe suivant manquant."
                    transitions.append({
                        "transition": line,
                        "paragraph_a": para_before,
                        "paragraph_b": para_after
                    })
                i += 1
        else:
            i += 1
    return transitions

# --- Few-shot JSON ---
def build_few_shot_json(pairs):
    return json.dumps([
        {
            "input": f"{pair['paragraph_a']}\nTRANSITION\n{pair['paragraph_b']}",
            "transition": pair['transition']
        } for pair in pairs
    ], ensure_ascii=False, indent=2)

# --- Fine-tuning JSONL ---
def build_fine_tuning_jsonl(pairs):
    lines = []
    for i, pair in enumerate(pairs):
        lines.append(json.dumps({
            "messages": [
                {"role": "user", "content": f"Paragraph A:\n{pair['paragraph_a']}\n\nParagraph B:\n{pair['paragraph_b']}"},
                {"role": "assistant", "content": pair['transition']}
            ]
        }, ensure_ascii=False))
    return "\n".join(lines)

# --- Streamlit UI ---
st.title("🪄 Transition Extractor & Formatter")

placeholder_count = st.number_input("🧮 Number of TRANSITION placeholders (estimation base)", min_value=1, step=1)
expected_transitions = placeholder_count * 3
st.markdown(f"📊 Expected transitions: **{expected_transitions}**")

sample_mode = st.toggle("⚙️ Limit to 10 transitions (sample mode)", value=True)
limit = 10 if sample_mode else None

uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

if uploaded_file is not None:
    with st.spinner("🔍 Processing document..."):
        try:
            pairs = extract_transitions_with_context(uploaded_file.read())
            if not pairs:
                st.warning("No valid transitions found.")
            else:
                if limit:
                    pairs = pairs[:limit]

                transitions_only = [p["transition"] for p in pairs]

                st.success(f"{len(pairs)} validated transitions {'(sample)' if sample_mode else ''}")
                st.write("📋 Sample Preview:")
                st.code("\n".join(transitions_only[:10]), language="text")

                st.download_button(
                    label="📥 Download Transitions (.txt)",
                    data="\n".join(transitions_only),
                    file_name="validated_transitions.txt",
                    mime="text/plain"
                )

                st.download_button(
                    label="📥 Download Few-Shot JSON (.json)",
                    data=build_few_shot_json(pairs),
                    file_name="few_shot_transitions.json",
                    mime="application/json"
                )

                st.download_button(
                    label="📥 Download Fine-Tuning JSONL (.jsonl)",
                    data=build_fine_tuning_jsonl(pairs),
                    file_name="fine_tuning_transitions.jsonl",
                    mime="application/jsonl"
                )
        except Exception as e:
            st.error(f"❌ Error: {e}")
