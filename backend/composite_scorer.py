"""
Composite Scorer v3
Fixes:
1. Education extraction - stricter patterns, no false matches
2. Experience relevance - domain-aware scoring
3. Semantic scoring - uses only relevant resume sections
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

from taxonomy import normalize_skill, skills_match_with_synonyms
from experience_extractor import extract_years_of_experience, score_experience as base_score_experience

# â”€â”€ Weights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DEFAULT_WEIGHTS = {
    "semantic":       0.40,
    "skills":         0.30,
    "experience":     0.15,
    "education":      0.10,
    "certifications": 0.05,
}

# â”€â”€ Education levels â€” STRICT patterns only â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Key fix: only match these as whole words with word boundaries
# Avoids "ms" matching "systems", "bs" matching "business", etc.
EDUCATION_PATTERNS = [
    # PhD
    (r"\bph\.?d\b",                                    6),
    (r"\bdoctor(?:ate|of philosophy)\b",                6),
    # Master's
    (r"\bmaster'?s?\s+(?:degree|of|in)\b",            5),
    (r"\bmaster\s+of\s+\w+",                          5),
    (r"\bm\.?s\.?\b",                                 5),
    (r"\bm\.?b\.?a\.?\b",                            5),
    (r"\bm\.?eng\.?\b",                               5),
    (r"\bm\.?sc\.?\b",                                5),
    (r"\bpostgraduate\b",                               5),
    (r"\bpgd\b",                                        5),
    # Bachelor's
    (r"\bbachelor'?s?\s+(?:degree|of|in)\b",          4),
    (r"\bbachelor\s+of\s+\w+",                        4),
    (r"\bb\.?s\.?\b",                                 4),
    (r"\bb\.?eng\.?\b",                               4),
    (r"\bb\.?a\.?\b",                                 4),
    (r"\bb\.?sc\.?\b",                                4),
    (r"\bundergraduate\b",                              4),
    (r"\bfirst\s+degree\b",                            4),
    (r"\bhons\.?\b",                                   4),
    # Associate / Advanced Diploma
    (r"\bassociate'?s?\s+degree\b",                    3),
    (r"\badvanced\s+diploma\b",                        3),
    (r"\bhigher\s+national\s+diploma\b",              3),
    (r"\bhnd\b",                                        3),
    (r"\bfoundation\s+degree\b",                       3),
    # Diploma
    (r"\bdiploma\b",                                    2),
    (r"\bhnc\b",                                        2),
    (r"\bcertificate\s+(?:of|in)\s+\w+",             2),
    (r"\bvocational\b",                                 2),
    # High school
    (r"\bhigh\s+school\b",                             1),
    (r"\bsecondary\s+school\b",                        1),
    (r"\ba\s+levels?\b",                               1),
    (r"\bgcse\b",                                       1),
    (r"\bmatriculation\b",                              1),
]

EDUCATION_RANK_TO_NAME = {
    1: "High School",
    2: "Diploma",
    3: "Advanced Diploma / Associate",
    4: "Bachelor's",
    5: "Master's",
    6: "PhD",
}

# â”€â”€ Domain keywords per industry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DOMAIN_KEYWORDS = {
    "technology":   [
        "software engineer", "software developer", "web developer", "programmer",
        "devops", "cloud engineer", "data engineer", "machine learning engineer",
        "frontend", "backend", "full stack", "api development",
        "linux", "docker", "kubernetes", "python developer", "java developer",
        "cybersecurity analyst", "network engineer", "systems administrator",
    ],
    "finance":      [
        "financial analysis", "financial analyst", "financial reporting",
        "accounting", "accountant", "auditing", "bookkeeping",
        "budgeting", "forecasting", "financial modeling",
        "gaap", "ifrs", "cpa", "cfa", "acca", "tax",
        "investment", "banking", "treasury", "cost analysis",
        "financial controller", "chief financial officer",
    ],
    "healthcare":   [
        "patient care", "clinical", "medical", "hospital", "nursing", "nurse",
        "physician", "doctor", "surgery", "diagnosis", "pharmacy",
        "healthcare", "ehr", "emr", "public health",
    ],
    "hr":           [
        "human resources", "hr manager", "hr officer", "recruitment",
        "talent acquisition", "employee relations", "performance management",
        "hr policies", "onboarding", "workforce planning",
    ],
    "marketing":    [
        "marketing manager", "digital marketing", "brand manager",
        "seo specialist", "social media", "content marketing",
        "campaign management", "market research", "advertising",
    ],
    "legal":        [
        "lawyer", "attorney", "legal counsel", "paralegal",
        "litigation", "contract law", "compliance officer", "regulatory",
    ],
    "engineering":  [
        "mechanical engineer", "civil engineer", "structural engineer",
        "electrical engineer", "autocad", "manufacturing", "construction",
        "hydraulics", "thermodynamics", "process engineer",
    ],
    "education":    [
        "teacher", "lecturer", "professor", "curriculum development",
        "classroom management", "academic", "tutoring", "e-learning",
    ],
}


def detect_domain(text: str) -> str:
    """Detect primary domain using phrase-level matching."""
    text_lower = text.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(len(kw.split()) for kw in keywords if kw in text_lower)
        scores[domain] = score
    if max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)





# â”€â”€ Fix 1: Strict education extraction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def extract_education_level(text: str) -> tuple[str, int]:
    """
    Extract highest education level using strict word-boundary patterns.
    Returns (level_name, rank).
    """
    text_lower = text.lower()
    highest_rank = 0
    highest_name = ""

    for pattern, rank in EDUCATION_PATTERNS:
        if re.search(pattern, text_lower):
            if rank > highest_rank:
                highest_rank = rank
                highest_name = EDUCATION_RANK_TO_NAME.get(rank, "")

    return highest_name, highest_rank


def score_education(resume_text: str, required_education: str | None) -> float:
    if not required_education:
        return 50.0

    # Get required rank â€” also check common shorthand like "Bachelor's", "Master's"
    req_lower = required_education.lower().strip()
    req_rank  = 0

    # Quick shorthand mapping first
    SHORTHAND = {
        "bachelor": 4, "bachelor's": 4, "bachelors": 4,
        "master": 5, "master's": 5, "masters": 5,
        "phd": 6, "doctorate": 6,
        "diploma": 2, "advanced diploma": 3,
        "associate": 3, "certificate": 2,
        "high school": 1, "secondary": 1,
    }
    for key, rank in SHORTHAND.items():
        if key in req_lower:
            req_rank = max(req_rank, rank)

    # Also try full patterns
    for pattern, rank in EDUCATION_PATTERNS:
        try:
            if re.search(pattern, req_lower):
                req_rank = max(req_rank, rank)
        except re.error:
            pass

    if req_rank == 0:
        return 50.0  # unrecognized requirement

    _, found_rank = extract_education_level(resume_text)

    if found_rank == 0:
        return 15.0  # no education detected

    if found_rank >= req_rank:
        return 100.0

    # Granular partial scoring based on gap
    gap = req_rank - found_rank
    if gap == 1:
        return 65.0   # one level below â€” e.g. Advanced Diploma vs Bachelor's
    elif gap == 2:
        return 40.0   # two levels below â€” e.g. Diploma vs Master's
    elif gap == 3:
        return 20.0   # three levels below
    else:
        return 10.0   # far below requirement


# â”€â”€ Fix 2: Domain-aware experience scoring â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def score_experience_domain_aware(
    resume_text:    str,
    required_years: int | None,
    job_text:       str,
) -> float:
    """
    Score experience considering domain relevance.
    If resume domain doesn't match job domain, penalize heavily.
    """
    if not required_years:
        return 50.0

    resume_domain = detect_domain(resume_text)
    job_domain    = detect_domain(job_text)

    years_found = extract_years_of_experience(resume_text)

    # Domain mismatch penalty
    if resume_domain != job_domain and job_domain != "general":
        # Different domain â€” max score is 30% regardless of years
        if years_found == 0:
            return 10.0
        if years_found >= required_years:
            return 30.0
        return round((years_found / required_years) * 20, 2)

    # Same domain â€” normal scoring
    if years_found == 0:
        return 20.0
    if years_found >= required_years:
        excess = years_found - required_years
        bonus  = min(excess * 5, 20)
        score  = min(100.0, 80.0 + bonus)

        # Overqualification soft penalty â€” very large excess experience
        # relative to what the role asks for is a real recruiter concern
        # (flight risk, salary mismatch, role under-utilization), so we
        # taper the score back down rather than letting it climb forever.
        if required_years > 0:
            ratio = years_found / required_years
            if ratio >= 4:
                # e.g. 8+ years for a job requiring 2 â€” heavily overqualified
                score = max(score - 15, 60.0)
            elif ratio >= 2.5:
                # moderately overqualified
                score = max(score - 7, 70.0)

        return round(score, 2)
    return round((years_found / required_years) * 75, 2)


def detect_overqualification(years_found: float, required_years: int | None) -> dict:
    """
    Flag overqualification as a separate signal recruiters can see,
    independent of the numeric experience score adjustment above.
    """
    if not required_years or required_years == 0 or years_found == 0:
        return {"is_overqualified": False, "ratio": None}

    ratio = round(years_found / required_years, 2)
    return {
        "is_overqualified": ratio >= 2.5,
        "ratio": ratio,
    }


# â”€â”€ Fix 3: Section-aware semantic scoring â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def extract_relevant_sections(text: str) -> str:
    """
    Extract only the most relevant sections for semantic comparison:
    Skills, Experience, Summary â€” ignore personal info, hobbies etc.
    """
    relevant_headers = {
        "skills", "technical skills", "work experience", "experience",
        "professional experience", "employment", "summary", "profile",
        "objective", "projects", "certifications", "qualifications",
        "core competencies", "expertise",
    }
    skip_headers = {
        "references", "hobbies", "interests", "personal information",
        "contact", "languages", "awards", "publications",
    }

    lines   = text.split("\n")
    result  = []
    capture = True  # capture by default
    current_section = ""

    for line in lines:
        clean = line.strip().lower()
        if clean in relevant_headers:
            capture = True
            current_section = clean
            result.append(line)
        elif clean in skip_headers:
            capture = False
        elif capture and line.strip():
            result.append(line)

    extracted = " ".join(result)
    # Fall back to full text if extraction is too short
    return extracted if len(extracted) > 200 else text


# â”€â”€ Certifications â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def score_certifications(
    resume_text:    str,
    resume_skills:  list[str],
    required_certs: list[str],
) -> tuple[float, list[str], list[str]]:
    if not required_certs:
        return 50.0, [], []

    text_lower          = resume_text.lower()
    resume_skills_lower = [normalize_skill(s).lower() for s in resume_skills]
    matched, missing    = [], []

    for cert in required_certs:
        canonical = normalize_skill(cert).lower()
        if (cert.lower() in text_lower or
                canonical in text_lower or
                canonical in resume_skills_lower):
            matched.append(cert)
        else:
            missing.append(cert)

    return round((len(matched) / len(required_certs)) * 100, 2), matched, missing


# â”€â”€ Result dataclass â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class ScoringResult:
    semantic_score:         float = 0.0
    skills_score:           float = 0.0
    experience_score:       float = 0.0
    education_score:        float = 0.0
    certification_score:    float = 0.0
    final_score:            float = 0.0
    matched_skills:         list[str] = field(default_factory=list)
    missing_skills:         list[str] = field(default_factory=list)
    matched_certs:          list[str] = field(default_factory=list)
    missing_certs:          list[str] = field(default_factory=list)
    experience_years_found: float     = 0.0
    education_level_found:  str       = ""
    resume_domain:          str       = ""
    job_domain:             str       = ""
    weights_used:           dict      = field(default_factory=dict)


# â”€â”€ Main composite scorer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def compute_composite_score(
    resume_text:         str,
    resume_skills:       list[str],
    semantic_score:      float,
    job_required_skills: list[str],
    job_required_certs:  list[str],
    job_min_experience:  int | None,
    job_education_level: str | None,
    job_text:            str = "",
    weights:             dict | None = None,
) -> ScoringResult:
    w = weights or DEFAULT_WEIGHTS

    # Fix 3: Use only relevant resume sections for semantic score
    relevant_text = extract_relevant_sections(resume_text)
    sem_score     = round(semantic_score, 2)

    # Skills with synonym normalization
    skills_result = skills_match_with_synonyms(resume_skills, job_required_skills, resume_text)
    skills_score  = round(skills_result["match_ratio"] * 100, 2)

    # Fix 2: Domain-aware experience scoring
    exp_score  = score_experience_domain_aware(resume_text, job_min_experience, job_text)
    exp_years  = extract_years_of_experience(resume_text)

    # Fix 1: Strict education extraction
    edu_name, _ = extract_education_level(resume_text)
    edu_score   = score_education(resume_text, job_education_level)

    # Certifications
    cert_score, matched_certs, missing_certs = score_certifications(
        resume_text, resume_skills, job_required_certs
    )

    # Weighted composite
    final = (
        w.get("semantic",       0.40) * sem_score    +
        w.get("skills",         0.30) * skills_score +
        w.get("experience",     0.15) * exp_score    +
        w.get("education",      0.10) * edu_score    +
        w.get("certifications", 0.05) * cert_score
    )

    return ScoringResult(
        semantic_score         = sem_score,
        skills_score           = skills_score,
        experience_score       = round(exp_score, 2),
        education_score        = round(edu_score, 2),
        certification_score    = cert_score,
        final_score            = round(final, 2),
        matched_skills         = skills_result["matched"],
        missing_skills         = skills_result["missing"],
        matched_certs          = matched_certs,
        missing_certs          = missing_certs,
        experience_years_found = exp_years,
        education_level_found  = edu_name,
        resume_domain          = detect_domain(resume_text),
        job_domain             = detect_domain(job_text),
        weights_used           = w,
    )
