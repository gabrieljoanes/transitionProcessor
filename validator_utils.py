import openai
import streamlit as st
import json

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def build_fewshots_with_gpt(paragraph: str, transitions: list, model="gpt-4") -> list:
    prompt = f"""
Tu es un assistant de rédaction locale. Voici un paragraphe long contenant trois phrases de transition (journalistiques) insérées manuellement : {', '.join(transitions)}.

Ta tâche est de repérer ces trois transitions dans le texte, et de créer trois exemples de type few-shot.

Pour chaque exemple :
- extrait la partie avant la transition (paragraphe A),
- note la transition exacte (transition),
- extrait la partie qui suit (paragraphe B),
- résume chaque paragraphe A et B en une ou deux phrases claires.

Réponds au format JSON suivant :
[
  {{
    "paragraph_a": "Résumé de la partie A",
    "transition": "la transition exacte",
    "paragraph_b": "Résumé de la partie B"
  }},
  ...
]
Voici le texte :

{paragraph}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        output = response.choices[0].message.content.strip()

        # Show raw output in Streamlit
        st.subheader("🧠 GPT Raw Output")
        st.code(output)

        # Attempt to extract JSON from output
        start = output.find("[")
        end = output.rfind("]") + 1
        json_text = output[start:end]
        parsed = json.loads(json_text)

        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        st.error(f"GPT few-shot builder failed: {e}")
        return []
