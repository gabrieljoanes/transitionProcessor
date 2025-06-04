# --- FILE: validator_utils.py ---
import openai
import streamlit as st

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

        # Try to load as JSON directly
        parsed = json.loads(output)
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        print("GPT few-shot builder failed:", e)
        return []
