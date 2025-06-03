# --- FILE: extract_fewshots.py ---
from docx import Document
import re
import json
from typing import List, Tuple
from collections import Counter
from validator_utils import is_transition as is_valid_transition_gpt

# Known transition openers
TRANSITION_PATTERNS = [
    "enfin", "dans l'actualité", "dans un autre registre", "et pour finir",
    "à noter que", "signalons que", "sachez que", "pour finir",
    "d'autre part", "tournons-nous", "partons à", "et pour terminer", "prenons", "nous vous rappelons"
]

# --- Helpers ---

def is_transition_line(line: str) -> bool:
    return any(line.lower().strip().startswith(pat) for pat in TRANSITION_PATTERNS)

def is_header_or_garbage(line: str) -> bool:
    line = line.strip().lower()
    return (
        line in {"transitions", "transitions :", "à savoir également"} or
        bool(re.match(r"^\d+\s+du\s+\d{2}/\d{2}", line)) or
        len(line) < 3
    )

def clean_paragraphs(doc_path: str) -> List[str]:
    doc = Document(doc_path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip() and not is_header_or_garbage(p.text)]

def split_paragraphs_on_multiple_transitions(paragraph: str) -> List[str]:
    """
    Split one long paragraph into chunks based on embedded transition phrases.
    """
    pattern = r"(?=\b(" + "|".join(re.escape(pat) for pat in TRANSITION_PATTERNS) + r")[\s,:])"
    parts = re.split(pattern, paragraph, flags=re.IGNORECASE)
    if not parts:
        return [paragraph]
    grouped = []
    buffer = ""
    for part in parts:
        if is_transition_line(part):
            if buffer:
                grouped.append(buffer.strip())
                buffer = ""
        buffer += part
    if buffer:
        grouped.append(buffer.strip())
    return grouped

def is_too_similar(a: str, b: str, threshold: float = 0.8) -> bool:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    return len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1) >= threshold

def is_transition_contextually_valid(a: str, t: str, b: str, use_gpt: bool, model: str) -> bool:
    if not use_gpt:
        return True
    try:
        return is_valid_transition_gpt(t, use_gpt=True, model_choice=model, context_a=a, context_b=b)
    except Exception as e:
        print(f"⚠️ GPT validation failed: {e}")
        return False

# --- Main function ---

def extract_few_shot_examples_and_jsonl(doc_path: str, use_gpt=True, model="gpt-4", limit: int = None) -> Tuple[str, str]:
    raw_paragraphs = clean_paragraphs(doc_path)
    all_segments = []

    # Step 1: Flatten and split long paragraphs
    for para in raw_paragraphs:
        if any(pat in para.lower() for pat in TRANSITION_PATTERNS):
            all_segments.extend(split_paragraphs_on_multiple_transitions(para))
        else:
            all_segments.append(para)

    # Step 2: Build A–T–B examples
    examples = []
    transition_usage = Counter()

    for i in range(len(all_segments) - 2):
        a, t, b = all_segments[i], all_segments[i + 1], all_segments[i + 2]

        # Only accept if t is a transition
        if not is_transition_line(t):
            continue
        if is_transition_line(a) or is_transition_line(b):
            continue
        if is_too_similar(a, b):
            continue
        if transition_usage[t] >= 3:
            continue
        if not is_transition_contextually_valid(a, t, b, use_gpt, model):
            continue

        examples.append({
            "paragraph_a": a,
            "transition": t,
            "paragraph_b": b
        })
        transition_usage[t] += 1

        if limit and len(examples) >= limit:
            break

    # Step 3: Format for output
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
