"""
Improved extractor.py
- Name extraction uses trained NER model (falls back to en_core_web_sm, then regex)
- Phone extraction handles international formats
- Email extraction robust
"""
import re
from pathlib import Path

# ── Email ─────────────────────────────────────────────────────────────────────

def extract_email(text: str) -> str | None:
    emails = re.findall(
        r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',
        text
    )
    return emails[0] if emails else None


# ── Phone ─────────────────────────────────────────────────────────────────────

def extract_phone(text: str) -> str | None:
    patterns = [
        r'\(\+\d{1,4}\)\s*[\d\s\-\.]{7,}',
        r'\+\d{1,4}[\s\-\.]?\(?\d+\)?[\d\s\-\.]{6,}',
        r'\+\d{7,15}',
        r'\b0\d{9,11}\b',
        r'\b\d{3}[\s\-\.]\d{3}[\s\-\.]\d{4}\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return None


# ── Name ──────────────────────────────────────────────────────────────────────

SKIP_LINES = {
    "curriculum vitae", "cv", "resume", "profile", "summary",
    "objective", "contact", "contact information", "personal information",
    "personal details", "about me", "introduction",
}

NOT_NAME_WORDS = {
    "email", "phone", "address", "linkedin", "github", "website",
    "mobile", "tel", "fax", "street", "avenue", "road", "city",
    "skills", "education", "experience", "languages", "certifications",
    "references", "projects", "awards", "achievements", "publications",
    "interests", "hobbies",
}


def _load_nlp():
    """Load trained NER model if available, fall back to base model."""
    import spacy
    trained = Path("models/resume_ner")
    if trained.exists():
        try:
            return spacy.load(trained)
        except Exception:
            pass
    try:
        return spacy.load("en_core_web_sm")
    except Exception:
        return None


def extract_name(text: str) -> str | None:
    # Strategy 1: NER model
    nlp = _load_nlp()
    if nlp:
        try:
            doc = nlp(text[:500])
            for ent in doc.ents:
                if ent.label_ == "PERSON" and len(ent.text.split()) >= 2:
                    return ent.text.strip()
        except Exception:
            pass

    # Strategy 2: First short capitalized line near top
    lines = text.split("\n")[:20]
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        if clean.lower() in SKIP_LINES:
            continue
        words = clean.split()
        if (2 <= len(words) <= 4
                and all(w[0].isupper() for w in words if w)
                and not any(char.isdigit() for char in clean)
                and not any(w.lower() in NOT_NAME_WORDS for w in words)
                and len(clean) < 60):
            return clean

    return None