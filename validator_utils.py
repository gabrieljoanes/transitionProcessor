# --- FILE: validator_utils.py ---
import openai
import streamlit as st

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Check if a string is a transition ---
def is_transition(phrase, use_gpt, model_choice):
    if not use_gpt:
        return True

    prompt = f"""Is the following phrase a short transition commonly used to connect paragraphs in a news or editorial article?\nPhrase: \"{phrase}\"\nRespond only with \"Yes\" or \"No\"."""

    response = client.chat.completions.create(
        model=model_choice,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip().lower() == "yes"
