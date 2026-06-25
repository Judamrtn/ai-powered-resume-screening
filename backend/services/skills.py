"""
Final Skills Extractor
Combines three strategies for maximum accuracy:
1. Keyword matching against 500+ ESCO multi-industry skills
2. Skills section focused matching
3. Contextual phrase extraction
4. NER model extraction (trained on 2467 real resumes)
"""
import re
from pathlib import Path
from esco_loader import get_all_skills_flat, get_skills_by_category
from taxonomy import normalize_skills

# ── Load skills from ESCO dataset ─────────────────────────────────────────────
_ALL_SKILLS    = get_all_skills_flat()
_SKILLS_BY_CAT = get_skills_by_category()
SOFT_SKILLS    = _SKILLS_BY_CAT.get("Soft Skills", [])
ALL_SKILLS     = _ALL_SKILLS

# ── Section headers ───────────────────────────────────────────────────────────
STOP_SECTIONS = {
    "education", "experience", "work experience", "employment",
    "languages", "language", "projects", "certifications",
    "references", "profile", "summary", "objective", "interests",
    "hobbies", "awards", "achievements", "publications",
}

SKILLS_HEADERS = {
    "skills", "technical skills", "core competencies", "competencies",
    "technologies", "tech stack", "expertise", "proficiencies",
    "tools & technologies", "tools and technologies", "key skills",
    "professional skills", "areas of expertise", "qualifications",
}

CONTEXT_PATTERNS = [
    (r'(?:experience|proficient|skilled|expertise|knowledge)\s+(?:in|with|of)\s+([\w\s\.\+\#\/]+?)(?:\s*[,\n]|$)', 1),
    (r'(?:developed|built|designed|implemented|deployed|created|managed)\s+(?:\w+\s+){0,3}(?:using|with|in)\s+([\w\s\.\+\#\/]+?)(?:\s*[,\n]|$)', 1),
    (r'([\w\.\+\#]+)\s+(?:developer|engineer|programmer|architect|specialist|analyst|manager|consultant)', 1),
    (r'certified\s+(?:in\s+)?([\w\s\.\+\#]+?)(?:\s*[,\n]|$)', 1),
]


def extract_skills_section(text: str) -> str:
    lines   = text.split("\n")
    section = []
    capture = False
    for line in lines:
        clean = line.strip().lower()
        if clean in SKILLS_HEADERS:
            capture = True
            continue
        if capture:
            if clean in STOP_SECTIONS:
                break
            if line.strip():
                section.append(line.strip())
    return " ".join(section)


def find_matches(text: str, skill_list: list) -> list:
    found = []
    for skill in skill_list:
        pattern = r'(?<![A-Za-z0-9])' + re.escape(skill) + r'(?![A-Za-z0-9])'
        for m in re.finditer(pattern, text, re.IGNORECASE):
            if not is_negated_mention(text, m.start()):
                found.append(skill)
                break  # one credited mention is enough to count the skill
    return found


# Phrases that, when found shortly before a skill mention, mean the
# candidate is explicitly disclaiming or has not yet acquired that
# skill — crediting it as a real skill would be a false positive that
# directly inflates skills_score for candidates who are simply being
# honest about their gaps.
NEGATION_PATTERNS = [
    r'\bno\s+experience\s+(?:with|in|using)\b',
    r'\bnot\s+(?:yet\s+)?(?:familiar|experienced|proficient|skilled)\s+(?:with|in)\b',
    r'\bwithout\s+(?:any\s+)?experience\s+(?:in|with)\b',
    r'\black(?:s|ing)?\s+(?:of\s+)?experience\s+(?:in|with)\b',
    r'\blimited\s+(?:exposure|experience|knowledge)\s+(?:to|in|with)\b',
    r'\bno\s+(?:prior\s+)?knowledge\s+of\b',
    r'\bcurrently\s+learning\b',
    r'\b(?:would\s+like|hope|hoping|eager|keen)\s+to\s+(?:learn|gain\s+experience\s+(?:in|with))\b',
    r'\bplanning\s+to\s+learn\b',
    r'\bnew\s+to\b',
    r'\bbeginner\s+(?:in|with|at)\b',
    r'\bunfamiliar\s+with\b',
]
_NEGATION_REGEX = re.compile("|".join(NEGATION_PATTERNS), re.IGNORECASE)

# How far back (characters) to look for a negation cue before the skill
# mention. Wide enough to catch "I have no experience with Python and
# Docker" (the cue is well before "Docker"), narrow enough to avoid
# bleeding into a previous, unrelated sentence.
NEGATION_LOOKBACK_CHARS = 60


def is_negated_mention(text: str, match_start: int) -> bool:
    """
    Check whether the skill mention at match_start is inside a negated
    or aspirational ("not yet acquired") context, by scanning backward
    within the same sentence/clause for a negation cue phrase.
    """
    window_start = max(0, match_start - NEGATION_LOOKBACK_CHARS)
    window       = text[window_start:match_start]

    # IMPORTANT: PDF-extracted text frequently contains single newlines
    # that are just visual line-wraps from the page layout, not real
    # sentence breaks (e.g. "...currently learning\nKubernetes..." is
    # ONE sentence split across two lines). Treating every "\n" as a
    # hard boundary would wrongly cut off a negation cue that continues
    # onto the next visual line. A DOUBLE newline ("\n\n", a blank line)
    # is a much more reliable signal of an actual paragraph/section
    # break, so only that — plus real sentence-ending punctuation — is
    # treated as a hard boundary. A lone "\n" is normalized to a space
    # before boundary detection so it never falsely resets scope.
    window = re.sub(r'(?<!\n)\n(?!\n)', ' ', window)

    hard_boundaries     = [".", "\n\n", ";"]
    contrast_boundaries = [
        m.end() for m in re.finditer(
            r',\s*(?:but|though|however|yet|although|except)\b',
            window, re.IGNORECASE,
        )
    ]

    last_cut = 0
    for boundary in hard_boundaries:
        idx = window.rfind(boundary)
        if idx != -1:
            last_cut = max(last_cut, idx + len(boundary))
    if contrast_boundaries:
        last_cut = max(last_cut, max(contrast_boundaries))

    window = window[last_cut:]

    return bool(_NEGATION_REGEX.search(window))


def extract_contextual_skills(text: str, skill_list: list) -> list:
    found       = set()
    skill_lower = {s.lower(): s for s in skill_list}
    for pattern, group in CONTEXT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            # Check negation relative to where the whole pattern starts,
            # not just the captured group — "no experience with" has its
            # negation cue ("no") sitting BEFORE the trigger word
            # ("experience"), which is itself before the captured skill
            # name, so the lookback must start from match.start().
            if is_negated_mention(text, match.start()):
                continue

            phrase = match.group(group).strip().lower()
            for skill_l, skill_orig in skill_lower.items():
                # Word-boundary check, not a raw substring check — a raw
                # `skill_l in phrase` check would let a single-letter skill
                # like "C" falsely match inside any word containing the
                # letter c (e.g. "corporate"), which is exactly what
                # happened before this fix. Very short skill tokens (<=2
                # chars) are additionally required to match a WHOLE word
                # in the phrase, not just appear with boundaries, since
                # boundary regex alone is still too permissive for things
                # like "C" or "R" sitting next to punctuation.
                if len(skill_l) <= 2:
                    phrase_words = re.findall(r"[\w\+\#]+", phrase)
                    if skill_l not in phrase_words:
                        continue
                else:
                    boundary_pattern = r'(?<![A-Za-z0-9])' + re.escape(skill_l) + r'(?![A-Za-z0-9])'
                    if not re.search(boundary_pattern, phrase):
                        continue
                found.add(skill_orig)
    return list(found)


def extract_skills_with_ner(text: str) -> list:
    """Extract skills using the trained NER model."""
    model_path = Path("models/resume_ner")
    if not model_path.exists():
        return []
    try:
        import importlib
        if importlib.util.find_spec("spacy") is None:
            return []
        spacy = importlib.import_module("spacy")
        nlp  = spacy.load(model_path)
        doc  = nlp(text[:3000])
        return [ent.text for ent in doc.ents if ent.label_ == "SKILL"]
    except Exception:
        return []


def has_any_non_negated_mention(text: str, skill: str) -> bool:
    """
    Check whether a skill has at least one mention in the text that is
    NOT inside a negated/aspirational context. Used as a final filter
    after combining results from all four extraction strategies, since
    strategies like the NER model have no awareness of negation and can
    otherwise reintroduce a skill that other strategies correctly
    excluded as disclaimed (e.g. "no experience with Python").
    """
    pattern = r'(?<![A-Za-z0-9])' + re.escape(skill) + r'(?![A-Za-z0-9])'
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    if not matches:
        # Skill wasn't found verbatim in the raw text at all (e.g. it
        # came from a synonym/contextual inference rather than a literal
        # mention) — don't penalize it, nothing to check negation against.
        return True
    return any(not is_negated_mention(text, m.start()) for m in matches)


def extract_skills(text: str) -> dict:
    """
    Extract skills using all four strategies combined.
    Returns normalized, deduplicated skill lists.
    """
    # Strategy 1: Full text keyword matching
    all_matched = find_matches(text, ALL_SKILLS)

    # Strategy 2: Skills section focused
    skills_section = extract_skills_section(text)
    if skills_section:
        section_matched = find_matches(skills_section, ALL_SKILLS)
        all_matched = list(set(all_matched + section_matched))

    # Strategy 3: Contextual phrases
    contextual  = extract_contextual_skills(text, ALL_SKILLS)
    all_matched = list(set(all_matched + contextual))

    # Strategy 4: NER model — this strategy has NO negation awareness,
    # so anything it adds must still pass the final negation filter below
    ner_skills  = extract_skills_with_ner(text)
    all_matched = list(set(all_matched + ner_skills))

    # Final negation pass over the COMBINED list — catches anything any
    # individual strategy missed, particularly the NER model which can't
    # see negation context at all.
    all_matched = [
        skill for skill in all_matched
        if has_any_non_negated_mention(text, skill)
    ]

    # Normalize using taxonomy (JS→JavaScript, k8s→Kubernetes, etc.)
    normalized = normalize_skills(all_matched)

    # Categorize
    soft_lower  = {s.lower() for s in SOFT_SKILLS}
    tech_skills = [s for s in normalized if s.lower() not in soft_lower]
    soft_skills = [s for s in normalized if s.lower() in soft_lower]

    return {
        "technical_skills": tech_skills,
        "soft_skills":      soft_skills,
        "tools":            [],
        "all_skills":       normalized,
    }