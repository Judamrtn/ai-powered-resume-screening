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
    """
    Extract phone numbers supporting international formats:
    +250 788 000 000, (+250)789 823 231, +1-800-555-0199,
    (555) 123-4567, 0712 345 678, +44 7911 123456

    Each pattern is bounded to stop at runs of 3+ spaces/tabs, which in
    practice almost always signal a column boundary in a multi-column
    resume layout rather than a continuation of the same phone number.
    """
    GAP = r'(?:[ \t]{1,2}|[\-\.])'  # allowed single-space/dash/dot separators within a number

    patterns = [
        # International with parenthesized country code: (+250) 789 823 231
        rf'\(\+\d{{1,4}}\){GAP}*\d(?:{GAP}?\d){{6,12}}',
        # Plain international: +250 788 000 000, +44 7911 123456
        rf'\+\d{{1,4}}{GAP}?\(?\d+\)?(?:{GAP}?\d){{5,12}}',
        r'\+\d{7,15}',
        # US-style with parenthesized area code, no country code: (555) 123-4567
        r'\(\d{3}\)\s*\d{3}[\s\-\.]\d{4}',
        # Local format starting with 0: 0712345678
        r'\b0\d{9,11}\b',
        # Plain dashed/dotted: 555-123-4567 or 555.123.4567
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

        # Guard against column-bleed: if a trailing word is ALL CAPS and
        # longer than 3 chars, it is almost certainly a section header
        # ("EXPERIENCE", "SKILLS") that leaked in from an adjacent column
        # in a two-column resume layout, rather than part of a real name.
        while words and len(words[-1]) > 3 and words[-1].isupper():
            words.pop()

        if not words:
            continue

        joined = " ".join(words)
        if (2 <= len(words) <= 4
                and all(w[0].isupper() for w in words if w)
                and not any(char.isdigit() for char in joined)
                and not any(w.lower() in NOT_NAME_WORDS for w in words)
                and len(joined) < 60):
            return joined

    return None