# --- FILE: extract_fewshots.py ---
from docx import Document
import re
import json
from typing import List, Tuple
from collections import Counter
from validator_utils import is_transition

# List of known transition phrases for detection
TRANSITION_PATTERNS = [
    "enfin", "dans l'actualité", "dans un autre registre", "et pour finir",
    "à noter que", "signalons que", "sachez que", "pour finir",
    "d'autre part", "tournons-nous", "partons à", "nous vous rappelons", "et pour terminer"
]

def is_transition_line(line: str) -> bool:
    line = line.strip().lower()
    return any(line.startswith(p) for p in TRANSITION_PATTERNS)

def is_header_or_garbage(line: str) -> bool:
    return (
        bool(re.match(r"^\d+\s+du\s+\d{2}/\d{2}", line)) or
        line.strip().lower().startswith("à savoir également")
    )

def clean_paragraphs(doc_path: str) -> List[str]:
    doc = Document(doc_path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]

def group_paragraphs_by_transitions(paragraphs: List[str]) -> List[Tuple[str, List[str]]]:
    """
    Groups paragraphs as (transition, [related_paragraphs]) blocks.
    """
    groups = []
    current_transition = None
    buffer = []

    for p in paragraphs:
        if is_header_or_garbage(p):
            continue
        if is_transition_line(p):
            if current_transition and buffer:
                groups.append((current_transition, buffer))
                buffer = []
            current_transition = p
        else:
            buffer.append(p)

    if current_transition and buffer:
        groups.append((current_transition, buffer))

    return groups

def is_too_similar(a: str, b: str, threshold: float = 0.8) -> bool:
    set_a, set_b = set(a.lower().split()), set(b.lower().split())
    overlap = len(set_a & set_b) / max(len(set_a | set_b), 1)
    return overlap >= threshold

def extract_few_shot_examples_and_jsonl(doc_path: str, use_gpt=True, model="gpt-4", limit: int = None) -> Tuple[str, str]:
    paragraphs = clean_paragraphs(doc_path)
    groups = group_paragraphs_by_transitions(paragraphs)
    examples = []
    transition_usage = Counter()

    for transition, paras in groups:
        if len(paras) < 2:
            continue

        for i in range(len(paras) - 1):
            para_a = paras[i]
            para_b = paras[i + 1]

            if is_transition_line(para_a):  # Should not be a transition
                continue
            if is_too_similar(para_a, para_b):
                continue
            if transition_usage[transition] >= 3:
                continue
            if use_gpt and not is_transition(transition, use_gpt=True, model_choice=model):
                continue

            examples.append({
                "paragraph_a": para_a,
                "transition": transition,
                "paragraph_b": para_b
            })
            transition_usage[transition] += 1

            if limit and len(examples) >= limit:
                break

        if limit and len(examples) >= limit:
            break

    # JSON and JSONL outputs
    fewshot_json = json.dumps(examples, ensure_ascii=False, indent=2)

    jsonl_lines = []
    for ex in examples:
        jsonl_lines.append(json.dumps({
            "messages": [
                {"role": "system", "content": "Insert a short, contextual transition between the two paragraphs."},
                {"role": "user", "content": f"Paragraph A: {ex['paragraph_a']}\nParagraph B: {ex['paragraph_b']}"},
                {"role": "assistant", "content": ex["transition"]}
            ]
        }, ensure_ascii=False))

    return fewshot_json, "\n".join(jsonl_lines)
