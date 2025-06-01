from docx import Document
import re
from typing import List, Dict, Tuple

# List of transitions to exclude due to overuse
COMMON_TRANSITIONS_TO_SKIP = {
    "Enfin, signalons que",
    "Enfin,",
    "Et pour finir,",
    "Enfin, dans l'actualité également,",
    "Dans un autre registre,"
}


def is_transition_line(line: str) -> bool:
    return line.strip().lower().startswith("transitions")


def is_header_or_garbage(line: str) -> bool:
    return bool(re.match(r"^\d+\s+du\s+\d{2}/\d{2}", line)) or \
           line.strip().lower().startswith("à savoir également")


def extract_paragraphs(doc_path: str) -> List[str]:
    doc = Document(doc_path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def extract_few_shot_examples_and_jsonl(doc_path: str, limit: int = None) -> Tuple[str, str]:
    paragraphs = extract_paragraphs(doc_path)
    examples = []
    buffer = []
    current_transitions = []
    collecting_transitions = False

    for para in paragraphs:
        if is_transition_line(para):
            collecting_transitions = True
            continue
        elif is_header_or_garbage(para):
            collecting_transitions = False
            continue

        if collecting_transitions:
            cleaned = para.strip()
            if cleaned not in COMMON_TRANSITIONS_TO_SKIP:
                current_transitions.append(cleaned)
        else:
            buffer.append(para.strip())
            if len(buffer) >= 2 and current_transitions:
                paragraph_a = buffer[-2]
                transition = current_transitions.pop(0)
                paragraph_b = buffer[-1]

                if transition in paragraph_a or transition in paragraph_b:
                    continue

                examples.append({
                    "paragraph_a": paragraph_a,
                    "transition": transition,
                    "paragraph_b": paragraph_b
                })

                if limit and len(examples) >= limit:
                    break

    # --- Export JSON ---
    fewshot_json = json_dumps_pretty(examples)

    # --- Export JSONL for fine-tuning ---
    fine_tune_lines = []
    for ex in examples:
        fine_tune_lines.append(json_dumps_pretty({
            "messages": [
                {"role": "system", "content": "Insert a short, contextual transition between the two paragraphs."},
                {"role": "user", "content": f"Paragraph A: {ex['paragraph_a']}\nParagraph B: {ex['paragraph_b']}"},
                {"role": "assistant", "content": ex["transition"]}
            ]
        }).strip())

    fine_tune_jsonl = "\n".join(fine_tune_lines)

    return fewshot_json, fine_tune_jsonl


def json_dumps_pretty(obj: Dict) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2)
