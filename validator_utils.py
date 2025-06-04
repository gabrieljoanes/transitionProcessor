import openai
import streamlit as st

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def summarize_with_gpt(text: str, model: str = "gpt-4") -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": f"Résume le paragraphe suivant en une seule phrase claire et concise :\n\n{text}"}
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("GPT summarization failed:", e)
        return text.split(".")[0].strip()
