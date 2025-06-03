# --- FILE: validator_utils.py ---
import openai
import streamlit as st

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def is_transition(phrase, use_gpt=True, model_choice="gpt-4", context_a=None, context_b=None):
    if not use_gpt:
        return True

    prompt = f"""Is this a suitable editorial transition to insert between two regional news paragraphs?

Paragraph A:
{context_a}

Transition:
{phrase}

Paragraph B:
{context_b}

Answer only Yes or No."""

    response = client.chat.completions.create(
        model=model_choice,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message.content.strip().lower() == "yes"
