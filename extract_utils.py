# --- FILE: extract_utils.py ---
import docx
import io
import re
from collections import Counter

# --- Extract transitions from DOCX ---
def extract_transitions_from_docx(docx_bytes):
    doc = docx.Document(io.BytesIO(docx_bytes))
    transitions_raw = []
    capture = False

    for para in doc.paragraphs:
        text = para.text.strip()
        if "transitions" in text.lower():
            capture = True
            continue
        if capture:
            if not text:
                break
            transitions_raw.append(text)
    return transitions_raw

# --- Filter out known non-transition patterns ---
def looks_like_date_or_invalid_code(phrase):
    if re.match(r"du\\s\\d{2}/?$", phrase, re.IGNORECASE):
        return True
    if phrase.lower().startswith("du ") and "/" in phrase:
        return True
    return False

# --- Normalize for strict deduplication ---
def normalize_strict(phrase):
    return re.sub(r'\\s+', ' ', phrase.strip())

