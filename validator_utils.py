# --- FILE: validator_utils.py ---
import openai
import streamlit as st

# Initialize OpenAI client
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Check if a string is a valid editorial transition ---
def is_transition(phrase, use_gpt=True, model_choice="gpt-4") -> bool:
    if not use_gpt:
        return True  # Bypass GPT validation if disabled

    prompt = (
        "Is the following phrase a short transition commonly used to connect paragraphs "
        "in a news or editorial article?\n"
        f'Phrase: "{phrase}"\n'
        'Respond only with "Yes" or "No".'
    )

    try:
        response = client.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )
        result = response.choices[0].message.content.strip().lower()
        return result == "yes"
    except Exception as e:
        print(f"⚠️ GPT validation failed for phrase '{phrase}': {e}")
        return False  # Fallback to rejecting if GPT call fails
