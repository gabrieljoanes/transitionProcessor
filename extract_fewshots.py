# extract_fewshots.py

from docx import Document
import re
from typing import List, Dict
from collections import defaultdict


def is_transition_line(line: str) -> bool:
    return line.strip().lower().startswith("transitions")


def is_header_or_garbage(line: str) -> bool:
    return bool(re.match(r"^\d+\s+du\s+\d{2}/\d{2}", line)) or \
           line.strip().lower().startswith("à savoir également")


def extract_paragraphs(doc_path: str) -> List[str]:
    doc = Document(doc_path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def extract_few_shot_examples(doc_path: str, limit: int = None, max_per_transition: int = 3) -> List[Dict[str, str]]:
    paragraphs = extract_paragraphs(doc_path)
    examples = []
    buffer = []
    current_transitions = []
    collecting_transitions = False
    transition_tracker = defaultdict(int)

    for para in paragraphs:
        if is_transition_line(para):
            collecting_transitions = True
            continue
        elif is_header_or_garbage(para):
            collecting_transitions = False
            continue

        if collecting_transitions:
            current_transitions.append(para.strip())
        else:
            buffer.append(para.strip())
            if len(buffer) >= 2 and current_transitions:
                paragraph_a = buffer[-2]
                transition = current_transitions.pop(0)
                paragraph_b = buffer[-1]

                if transition in paragraph_a or transition in paragraph_b:
                    continue

                if transition_tracker[transition] >= max_per_transition:
                    continue

                examples.append({
                    "paragraph_a": paragraph_a,
                    "transition": transition,
                    "paragraph_b": paragraph_b
                })
                transition_tracker[transition] += 1

                if limit and len(examples) >= limit:
                    break

    return examples


def convert_to_fine_tuning_format(fewshot_examples: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        {
            "messages": [
                {"role": "user", "content": f"{ex['paragraph_a']} <TRANSITION> {ex['paragraph_b']}"},
                {"role": "assistant", "content": ex["transition"]}
            ]
        }
        for ex in fewshot_examples
    ]
