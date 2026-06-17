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
        if re.search(pattern, text, re.IGNORECASE):
            found.append(skill)
    return found


def extract_contextual_skills(text: str, skill_list: list) -> list:
    found       = set()
    skill_lower = {s.lower(): s for s in skill_list}
    for pattern, group in CONTEXT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
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
        import spacy
        nlp  = spacy.load(model_path)
        doc  = nlp(text[:3000])
        return [ent.text for ent in doc.ents if ent.label_ == "SKILL"]
    except Exception:
        return []


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

    # Strategy 4: NER model
    ner_skills  = extract_skills_with_ner(text)
    all_matched = list(set(all_matched + ner_skills))

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