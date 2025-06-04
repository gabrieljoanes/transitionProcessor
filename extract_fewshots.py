# --- FILE: extract_fewshots.py ---
import json
from docx import Document
from typing import List, Tuple
from validator_utils import build_fewshots_with_gpt

TRANSITION_MARKER = "À savoir également dans votre département"
TRANSITION_LIST_MARKER = "Transitions :"

def clean_paragraphs(path: str) -> List[str]:
    doc = Document(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]

def extract_section_after_marker(paragraphs: List[str], marker: str) -> List[str]:
    for i, p in enumerate(paragraphs):
        if p.strip().lower().startswith(marker.lower()):
            return paragraphs[i+1:]
    return []

def extract_transitions_used(paragraphs: List[str]) -> List[str]:
    for i, p in enumerate(paragraphs):
        if p.strip().lower().startswith(TRANSITION_LIST_MARKER.lower()):
            return [t.strip() for t in paragraphs[i+1:i+4]]
    return []

def extract_long_paragraphs(paragraphs: List[str]) -> List[str]:
    return [p for p in paragraphs if len(p.split()) > 100]

def extract_few_shot_examples_and_jsonl(doc_path, use_gpt=True, model="gpt-4", limit=None) -> Tuple[str, str]:
    paragraphs = clean_paragraphs(doc_path)
    section = extract_section_after_marker(paragraphs, TRANSITION_MARKER)
    transitions = extract_transitions_used(paragraphs)

    if not section or not transitions:
        return json.dumps([], indent=2), ""

    long_paragraphs = extract_long_paragraphs(section)
    all_results = []

    for para in long_paragraphs:
        if use_gpt:
            fewshots = build_fewshots_with_gpt(para, transitions, model=model)
        else:
            continue  # fallback logic not implemented in this mode

        all_results.extend(fewshots)
        if limit and len(all_results) >= limit:
            all_results = all_results[:limit]
            break

    jsonl_lines = []
    for ex in all_results:
        jsonl_lines.append(json.dumps({
            "messages": [
                {"role": "system", "content": "Insert a short, contextual transition between the two paragraphs."},
                {"role": "user", "content": f"Paragraph A: {ex['paragraph_a']}\nParagraph B: {ex['paragraph_b']}"},
                {"role": "assistant", "content": ex["transition"]}
            ]
        }, ensure_ascii=False))

    return json.dumps(all_results, indent=2, ensure_ascii=False), "\n".join(jsonl_lines)
