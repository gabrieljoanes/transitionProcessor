import re
import json
from docx import Document
from typing import List, Tuple
from validator_utils import summarize_with_gpt
from collections import Counter

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

def split_paragraph_by_transitions(text: str, transitions: List[str]) -> List[Tuple[str, str, str]]:
    """Splits one long paragraph by transitions into A–T–B triplets."""
    output = []
    pattern = '|'.join(map(re.escape, transitions))
    segments = re.split(f"(?=\\b(?:{pattern}))", text)
    if len(segments) < 2:
        return []

    for i in range(len(segments) - 1):
        a = segments[i].strip()
        t_match = re.match(rf"({'|'.join(map(re.escape, transitions))})", segments[i+1].strip())
        if t_match:
            t = t_match.group(1)
            b = segments[i+1][len(t):].strip()
            output.append((a, t, b))
    return output

def extract_transitions_used(paragraphs: List[str]) -> List[str]:
    for i, p in enumerate(paragraphs):
        if p.strip().lower().startswith(TRANSITION_LIST_MARKER.lower()):
            return [t.strip() for t in paragraphs[i+1:i+4]]
    return []

def extract_few_shot_examples_and_jsonl(doc_path, use_gpt=True, model="gpt-4", limit=None) -> Tuple[str, str]:
    paragraphs = clean_paragraphs(doc_path)
    rest = extract_section_after_marker(paragraphs, TRANSITION_MARKER)
    if not rest:
        return json.dumps([], indent=2), ""

    try:
        long_block = next(p for p in rest if len(p.split()) > 100)
        transitions = extract_transitions_used(paragraphs)
    except StopIteration:
        return json.dumps([], indent=2), ""

    triples = split_paragraph_by_transitions(long_block, transitions)
    results = []
    jsonl_lines = []

    for a, t, b in triples[:limit or len(triples)]:
        if use_gpt:
            a_s = summarize_with_gpt(a, model=model)
            b_s = summarize_with_gpt(b, model=model)
        else:
            a_s = a.split(".")[0].strip()
            b_s = b.split(".")[0].strip()

        results.append({
            "paragraph_a": a_s,
            "transition": t,
            "paragraph_b": b_s
        })

        jsonl_lines.append(json.dumps({
            "messages": [
                {"role": "system", "content": "Insert a short, contextual transition between the two paragraphs."},
                {"role": "user", "content": f"Paragraph A: {a_s}\nParagraph B: {b_s}"},
                {"role": "assistant", "content": t}
            ]
        }, ensure_ascii=False))

    return json.dumps(results, indent=2, ensure_ascii=False), "\n".join(jsonl_lines)
