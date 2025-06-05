import docx
import io
import re
from typing import List, Tuple, Dict
import openai
import streamlit as st

# --- GPT Setup ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Constants ---
MARKER = "À savoir également dans votre département"
TRANSITION_HEADER = "Transitions :"

# --- Utilities ---
def extract_doc_text(docx_bytes: bytes) -> List[str]:
    doc = docx.Document(io.BytesIO(docx_bytes))
    return [para.text.strip() for para in doc.paragraphs if para.text.strip()]

def extract_transition_list(lines: List[str]) -> List[str]:
    transitions = []
    for i, line in enumerate(lines):
        if line.startswith(TRANSITION_HEADER):
            transitions = [l.strip() for l in lines[i+1:] if l.strip()]
            break
    return transitions

def extract_long_paragraph_after_marker(lines: List[str]) -> str:
    try:
        marker_index = lines.index(MARKER)
        return " ".join(lines[marker_index+1:])
    except ValueError:
        return ""

def summarize(paragraph: str, model="gpt-4") -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": f"Résume ce paragraphe de manière claire et concise (2 phrases max) :\n{paragraph}"
        }]
    )
    return response.choices[0].message.content.strip()

def generate_few_shot_examples_from_transitions(
    full_text: str,
    transitions: List[str],
    use_gpt: bool = False,
    model: str = "gpt-4"
) -> List[Dict[str, str]]:
    examples = []
    segments = re.split(r'(?<=\.)\s+(?=' + '|'.join(map(re.escape, transitions)) + r')', full_text)
    
    if len(segments) < 2:
        return []

    for i in range(len(segments) - 1):
        for transition in transitions:
            if segments[i+1].strip().startswith(transition):
                para_a = segments[i].strip()
                para_b = segments[i+1].replace(transition, '').strip()

                if use_gpt:
                    para_a = summarize(para_a, model)
                    para_b = summarize(para_b, model)

                examples.append({
                    "paragraph_a": para_a,
                    "transition": transition,
                    "paragraph_b": para_b
                })
                break
    return examples
