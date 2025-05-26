import streamlit as st
import docx
import io
import json
import openai

# --- OpenAI client setup (called dynamically) ---
def get_openai_client():
    return openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Heuristic transition filter ---
def is_transition_candidate(phrase):
    return 2 <= len(phrase.split()) <= 7 and phrase[0].isupper() and phrase[-1] in {'.', ',', ':'}

# --- GPT validation ---
def is_validated_by_gpt(phrase, model):
    client = get_openai_client()
    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?\nPhrase: "{phrase}"\nRespond only with "Yes" or "No"."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().lower() == "yes"

# --- Extract transition paragraph contexts ---
def extract_transitions(docx_bytes, use_gpt=False, gpt_model="gpt-3.5-turbo", limit=2):
    doc = docx.Document(io.BytesIO(docx_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip() and "transitions" not in p.text.lower()]
    results = []

    for i in range(1, len(paragraphs) - 1):
        middle = paragraphs[i]
        if is_transition_candidate(middle):
            cleaned = middle.rstrip(".:,; ")
            if use_gpt:
                if not is_validated_by_gpt(cleaned, gpt_model):
                    continue
            results.append({
                "transition": cleaned,
                "paragraph_a": paragraphs[i - 1],
                "paragraph_b": paragraphs[i + 1]
            })
            if limit and len(results) >= limit:
                break
    return results

# --- Few-shot format ---
def build_few_shot_json(pairs):
    return json.dumps([
        {
            "input": f"{pair['paragraph_a']}\nTRANSITION\n{pair['paragraph_b']}",
            "transition": pair['transition']
        } for pair in pairs
    ], ensure_ascii=False, indent=2)

# --- Fine-tuning format (OpenAI JSONL) ---
def build_fine_tuning_jsonl(pairs):
    return "\n".join([
        json.dumps({
            "messages": [
                {"role": "user", "content": f"Paragraph A:\n{pair['paragraph_a']}\n\nParagraph B:\n{pair['paragraph_b']}"},
                {"role": "assistant", "content": pair['transition']}
            ]
        }, ensure_ascii=False)
        for pair in pairs
    ])

# --- Streamlit UI ---
st.title("🪄 Transition Extractor (Few-Shot & Fine-Tune Ready)")

uploaded_file = st.file_uploader("📄 Upload your Word (.docx) file", type=["docx"])

use_gpt = st.checkbox("🤖 Use GPT to validate transitions")
gpt_model = st.radio("🧠 Select GPT model", options=["gpt-3.5-turbo", "gpt-4"], index=0, disabled=not use_gpt)

sample_mode = st.checkbox("⚙️ Sample mode: limit to 2 transitions", value=True)
limit = 2 if sample_mode else None

if uploaded_file:
    with st.spinner("🔍 Extracting transitions..."):
        try:
            pairs = extract_transitions(
                docx_bytes=uploaded_file.read(),
                use_gpt=use_gpt,
                gpt_model=gpt_model,
                limit=limit
            )

            if not pairs:
                st.warning("⚠️ No valid transitions found.")
            else:
                transitions_only = [p["transition"] for p in pairs]

                st.success(f"✅ Found {len(pairs)} transition(s)")
                st.code("\n".join(transitions_only), language="text")

                st.download_button(
                    label="📥 Download Transitions (.txt)",
                    data="\n".join(transitions_only),
                    file_name="transitions.txt",
                    mime="text/plain"
                )

                st.download_button(
                    label="📥 Download Few-Shot Format (.json)",
                    data=build_few_shot_json(pairs),
                    file_name="few_shot_transitions.json",
                    mime="application/json"
                )

                st.download_button(
                    label="📥 Download Fine-Tuning Format (.jsonl)",
                    data=build_fine_tuning_jsonl(pairs),
                    file_name="fine_tuning_transitions.jsonl",
                    mime="application/jsonl"
                )

        except Exception as e:
            st.error(f"❌ Error: {e}")
