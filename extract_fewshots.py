from docx import Document
import re
import json
from typing import List, Dict
from collections import Counter


def is_transition_line(line: str) -> bool:
    return line.strip().lower().startswith("transitions")


def is_header_or_garbage(line: str) -> bool:
    return bool(re.match(r"^\d+\s+du\s+\d{2}/\d{2}", line)) or \
           line.strip().lower().startswith("à savoir également")


def extract_paragraphs(doc_path: str) -> List[str]:
    doc = Document(doc_path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def extract_few_shot_examples_and_jsonl(doc_path: str, limit: int = None) -> (str, str):
    paragraphs = extract_paragraphs(doc_path)
    examples = []
    buffer = []
    current_transitions = []
    collecting_transitions = False
    transition_usage = Counter()

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
                paragraph_b = buffer[-1]
                transition = current_transitions.pop(0)

                # Enforce usage cap: no more than 3 uses of a given transition
                if transition_usage[transition] >= 3:
                    continue

                if transition in paragraph_a or transition in paragraph_b:
                    continue

                examples.append({
                    "paragraph_a": paragraph_a,
                    "transition": transition,
                    "paragraph_b": paragraph_b
                })
                transition_usage[transition] += 1

                if limit and len(examples) >= limit:
                    break

    # Create fewshot JSON
    fewshot_json = json.dumps(examples, ensure_ascii=False, indent=2)

    # Create fine-tuning JSONL format
    jsonl_lines = []
    for ex in examples:
        item = {
            "messages": [
                {"role": "system", "content": "Insert a short, contextual transition between the two paragraphs."},
                {"role": "user", "content": f"Paragraph A: {ex['paragraph_a']}\nParagraph B: {ex['paragraph_b']}"},
                {"role": "assistant", "content": ex["transition"]}
            ]
        }
        jsonl_lines.append(json.dumps(item, ensure_ascii=False))

    fine_tune_jsonl = "\n".join(jsonl_lines)
    return fewshot_json, fine_tune_jsonl
