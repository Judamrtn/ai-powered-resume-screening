"""
Intelligent Resume Scoring Engine
Implements 10 advanced scoring signals beyond simple keyword matching:

1. Contextual skill understanding
2. Career progression scoring
3. Skill recency weighting
4. Implicit skill inference
5. Resume quality scoring
6. Job title relevance
7. Industry experience matching
8. Education field relevance
9. Certification credibility
10. Red flags detection
"""
from __future__ import annotations
from contextual_extractor import extract_contextual_skills
import re
from dataclasses import dataclass, field
from datetime import datetime

CURRENT_YEAR = datetime.now().year

# Contextual skill extraction moved to contextual_extractor.py


# ── 2. Career Progression Scoring ────────────────────────────────────────────

SENIORITY_LEVELS = {
    "intern": 0, "trainee": 0, "graduate": 1,
    "junior": 1, "associate": 2, "mid": 3,
    "senior": 4, "lead": 5, "principal": 5,
    "staff": 5, "manager": 5, "director": 6,
    "head": 6, "vp": 7, "vice president": 7,
    "cto": 8, "ceo": 8, "chief": 8,
}

def extract_seniority_levels(text: str) -> list[int]:
    """Extract all seniority levels mentioned in resume."""
    text_lower = text.lower()
    levels = []
    for title, level in SENIORITY_LEVELS.items():
        if re.search(r'\b' + re.escape(title) + r'\b', text_lower):
            levels.append(level)
    return sorted(levels)

def score_career_progression(text: str) -> float:
    """
    Score based on career trajectory.
    Upward progression scores higher than stagnation.
    """
    levels = extract_seniority_levels(text)
    if not levels:
        return 50.0  # neutral
    if len(levels) == 1:
        # Single level found — score based on seniority
        return min(40 + levels[0] * 10, 100)
    # Multiple levels — reward upward progression
    progression = levels[-1] - levels[0]
    max_level   = levels[-1]
    base_score  = min(40 + max_level * 8, 80)
    prog_bonus  = min(progression * 5, 20)
    return min(base_score + prog_bonus, 100)


# ── 3. Skill Recency Weighting ────────────────────────────────────────────────

def extract_skill_years(text: str, skill: str) -> list[int]:
    """Find years mentioned near a skill to estimate recency."""
    years = []
    pattern = re.compile(
        r'(?:' + re.escape(skill) + r'.{0,100}(\d{4})|(\d{4}).{0,100}' + re.escape(skill) + r')',
        re.IGNORECASE | re.DOTALL
    )
    for match in pattern.finditer(text):
        year = int(match.group(1) or match.group(2))
        if 2000 <= year <= CURRENT_YEAR:
            years.append(year)
    return years

def recency_weight(year: int) -> float:
    """More recent = higher weight. Linear decay over 10 years."""
    age = CURRENT_YEAR - year
    if age <= 1:   return 1.0
    if age <= 3:   return 0.9
    if age <= 5:   return 0.75
    if age <= 7:   return 0.6
    if age <= 10:  return 0.4
    return 0.2

def score_skills_with_recency(
    resume_text: str,
    matched_skills: list[str],
    job_skills: list[str],
) -> float:
    """Score skills weighted by how recently they were used."""
    if not job_skills:
        return 0.0
    total_weight = 0.0
    for skill in matched_skills:
        years = extract_skill_years(resume_text, skill)
        if years:
            weight = max(recency_weight(y) for y in years)
        else:
            weight = 0.7  # found but no year context — moderate weight
        total_weight += weight
    max_possible = len(job_skills)
    return round((total_weight / max_possible) * 100, 2)


# ── 4. Implicit Skill Inference ───────────────────────────────────────────────

IMPLICIT_SKILL_MAP = {
    "REST APIs":          ["HTTP", "JSON", "API Design", "Web Services"],
    "FastAPI":            ["Python", "REST APIs", "Async Programming"],
    "Django":             ["Python", "REST APIs", "ORM", "MVC"],
    "React":              ["JavaScript", "HTML", "CSS", "Frontend"],
    "Docker":             ["Linux", "DevOps", "Containerization"],
    "Kubernetes":         ["Docker", "DevOps", "Cloud", "Linux"],
    "Machine Learning":   ["Python", "Statistics", "Data Analysis", "NumPy"],
    "Data Science":       ["Python", "Statistics", "Data Analysis", "Visualization"],
    "AWS":                ["Cloud", "DevOps", "Linux"],
    "Recruitment":        ["Interviewing", "Talent Acquisition", "HR"],
    "Performance Management": ["HR", "Goal Setting", "Employee Relations"],
    "Financial Analysis": ["Excel", "Accounting", "Data Analysis"],
    "Project Management": ["Planning", "Risk Management", "Stakeholder Management"],
    "Surgery":            ["Anatomy", "Clinical Skills", "Patient Care"],
    "SEO":                ["Google Analytics", "Content Marketing", "Digital Marketing"],
}

def infer_implicit_skills(detected_skills: list[str]) -> list[str]:
    """Infer additional skills based on detected skills."""
    inferred = set()
    detected_lower = {s.lower() for s in detected_skills}
    for skill, implied in IMPLICIT_SKILL_MAP.items():
        if skill.lower() in detected_lower:
            for imp in implied:
                if imp.lower() not in detected_lower:
                    inferred.add(imp)
    return list(inferred)


# ── 5. Resume Quality Scoring ─────────────────────────────────────────────────

QUANTIFIED_PATTERNS = [
    r'\d+%',                           # percentages
    r'\$[\d,]+',                       # dollar amounts
    r'increased\s+\w+\s+by\s+\d+',    # increased X by N
    r'reduced\s+\w+\s+by\s+\d+',      # reduced X by N
    r'managed\s+\w+\s+of\s+\d+',      # managed team of N
    r'served\s+\d+\s+\w+',            # served N customers
    r'\d+\+?\s+(?:clients?|customers?|users?|projects?|employees?)',
]

VAGUE_PATTERNS = [
    r'\bresponsible\s+for\b',
    r'\bworked\s+on\b',
    r'\bhelped\s+with\b',
    r'\binvolved\s+in\b',
    r'\bassisted\s+with\b',
]

def score_resume_quality(text: str) -> float:
    """
    Score resume quality based on:
    - Quantified achievements (higher = better)
    - Vague language (lower = worse)
    - Length and structure
    """
    text_lower = text.lower()

    # Count quantified achievements
    quantified = sum(
        len(re.findall(p, text_lower))
        for p in QUANTIFIED_PATTERNS
    )

    # Count vague statements
    vague = sum(
        len(re.findall(p, text_lower))
        for p in VAGUE_PATTERNS
    )

    # Word count score (300-800 words is ideal)
    word_count = len(text.split())
    if word_count < 100:   length_score = 20
    elif word_count < 300: length_score = 50
    elif word_count < 800: length_score = 100
    elif word_count < 1500: length_score = 80
    else:                   length_score = 60

    # Section structure
    has_sections = sum(1 for s in [
        "experience", "education", "skills", "summary"
    ] if s in text_lower)
    structure_score = min(has_sections * 25, 100)

    # Combine
    achievement_score = min(quantified * 15, 60)
    vague_penalty     = min(vague * 5, 30)
    quality = (
        0.35 * achievement_score +
        0.25 * structure_score   +
        0.25 * length_score      +
        0.15 * 50                # baseline
    ) - vague_penalty

    return max(round(quality, 2), 0)


# ── 6. Job Title Relevance ────────────────────────────────────────────────────

def score_job_title_relevance(resume_text: str, job_title: str) -> float:
    """Score how closely previous job titles match the target role."""
    if not job_title:
        return 50.0

    job_words = set(re.findall(r'\b\w+\b', job_title.lower()))
    job_words -= {"and", "or", "the", "a", "an", "of", "in", "for"}

    # Extract job titles from resume
    title_pattern = r'(?:^|\n)([A-Z][A-Za-z\s]+(?:Engineer|Developer|Manager|Analyst|'
    title_pattern += r'Director|Specialist|Consultant|Officer|Coordinator|Nurse|Doctor|'
    title_pattern += r'Teacher|Accountant|Designer|Architect|Administrator))'

    resume_titles = re.findall(title_pattern, resume_text, re.MULTILINE)
    if not resume_titles:
        return 30.0

    best_match = 0.0
    for title in resume_titles:
        title_words = set(re.findall(r'\b\w+\b', title.lower()))
        if not title_words:
            continue
        overlap = len(job_words & title_words) / max(len(job_words), 1)
        best_match = max(best_match, overlap)

    return round(best_match * 100, 2)


# ── 7. Industry Experience Matching ──────────────────────────────────────────

INDUSTRY_KEYWORDS = {
    # Technology — only core software/IT terms, NOT financial tools
    "technology":   [
        "software engineer", "software developer", "web developer", "programmer",
        "devops", "cloud engineer", "data engineer", "machine learning engineer",
        "frontend", "backend", "full stack", "api development", "microservices",
        "linux", "docker", "kubernetes", "python developer", "java developer",
        "javascript developer", "mobile developer", "cybersecurity analyst",
        "network engineer", "systems administrator", "database administrator",
    ],
    # Finance — strong finance-specific terms
    "finance":      [
        "financial analysis", "financial analyst", "financial reporting",
        "accounting", "accountant", "auditing", "auditor", "bookkeeping",
        "budget", "budgeting", "forecasting", "financial modeling",
        "accounts payable", "accounts receivable", "general ledger",
        "balance sheet", "income statement", "cash flow",
        "gaap", "ifrs", "cpa", "cfa", "acca", "tax", "taxation",
        "investment", "portfolio", "asset management", "banking",
        "financial controller", "chief financial officer", "cfo",
        "treasury", "payroll", "cost analysis", "variance analysis",
        "profit and loss", "p&l", "revenue", "expense",
    ],
    # Healthcare
    "healthcare":   [
        "patient care", "clinical", "medical", "hospital", "nursing", "nurse",
        "physician", "doctor", "surgery", "diagnosis", "treatment",
        "pharmacy", "pharmacist", "healthcare", "health care",
        "medical records", "ehr", "emr", "clinical trials",
        "public health", "epidemiology", "physiotherapy", "dentistry",
    ],
    # HR
    "hr":           [
        "human resources", "hr manager", "hr officer", "hr generalist",
        "recruitment", "talent acquisition", "employee relations",
        "performance management", "hr policies", "onboarding",
        "workforce planning", "compensation and benefits",
        "organizational development", "hris", "people operations",
    ],
    # Marketing
    "marketing":    [
        "marketing manager", "digital marketing", "brand manager",
        "seo specialist", "social media manager", "content marketing",
        "campaign management", "market research", "advertising",
        "lead generation", "marketing analyst", "growth hacking",
        "email marketing", "influencer marketing", "public relations",
    ],
    # Legal
    "legal":        [
        "lawyer", "attorney", "legal counsel", "paralegal",
        "litigation", "contract law", "corporate law", "legal advisor",
        "compliance officer", "regulatory", "arbitration",
        "intellectual property", "patent", "legal research",
    ],
    # Engineering (non-IT)
    "engineering":  [
        "mechanical engineer", "civil engineer", "structural engineer",
        "electrical engineer", "chemical engineer", "autocad",
        "manufacturing", "construction", "hydraulics", "thermodynamics",
        "project engineer", "process engineer", "quality engineer",
        "welding", "fabrication", "commissioning",
    ],
    # Education
    "education":    [
        "teacher", "lecturer", "professor", "instructor",
        "curriculum development", "lesson planning", "classroom management",
        "academic", "school", "university", "tutoring", "e-learning",
        "educational technology", "student assessment",
    ],
    # Logistics
    "logistics":    [
        "supply chain", "logistics manager", "warehouse manager",
        "inventory management", "freight", "shipping", "procurement",
        "demand planning", "distribution", "transport",
    ],
    # Construction
    "construction": [
        "site manager", "construction manager", "quantity surveyor",
        "civil works", "building contractor", "structural works",
        "project site", "blueprint", "bill of quantities",
    ],
}


def detect_industry(text: str) -> str:
    """
    Detect primary industry using weighted phrase-level matching.
    Multi-word keywords score higher to avoid false positives.
    """
    text_lower = text.lower()
    scores = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(len(kw.split()) for kw in keywords if kw in text_lower)
        scores[industry] = score
    if max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)




def score_industry_match(resume_text: str, job_text: str) -> float:
    resume_industry = detect_industry(resume_text)
    job_industry    = detect_industry(job_text)
    if resume_industry == job_industry:
        return 100.0
    if job_industry == "general" or resume_industry == "general":
        return 60.0
    return 20.0


# ── 8. Education Field Relevance ──────────────────────────────────────────────

FIELD_RELEVANCE = {
    "computer science":     ["technology", "software", "data", "it"],
    "information technology": ["technology", "software", "it", "systems"],
    "engineering":          ["technology", "manufacturing", "construction", "energy"],
    "business":             ["finance", "marketing", "hr", "management"],
    "accounting":           ["finance", "audit", "tax"],
    "marketing":            ["marketing", "sales", "advertising"],
    "nursing":              ["healthcare", "clinical"],
    "medicine":             ["healthcare", "clinical", "research"],
    "law":                  ["legal", "compliance", "governance"],
    "psychology":           ["hr", "healthcare", "education", "counseling"],
    "education":            ["teaching", "training", "academic"],
    "data science":         ["technology", "research", "analytics"],
}

def score_education_field(resume_text: str, job_text: str) -> float:
    """Score whether education field is relevant to the job."""
    text_lower    = resume_text.lower()
    job_lower     = job_text.lower()
    best_score    = 40.0  # default — education field unknown

    for field, relevant_domains in FIELD_RELEVANCE.items():
        if field in text_lower:
            # Check if any relevant domain appears in job
            matches = sum(1 for d in relevant_domains if d in job_lower)
            if matches > 0:
                field_score = min(60 + matches * 15, 100)
                best_score  = max(best_score, field_score)

    return best_score


# ── 9. Certification Credibility ─────────────────────────────────────────────

# Certifications with known validity periods (years)
CERT_VALIDITY = {
    "pmp":      3, "aws certified": 3, "google certified": 3,
    "cissp":    3, "ceh":    3, "ccna": 3, "ccnp": 3,
    "cpa":      1, "cfa":    1, "acca": 1,
    "shrm":     3, "phr":    3, "sphr": 3,
    "scrum master": 2, "prince2": 5, "itil": 3,
    "six sigma": 0,  # no expiry
}

def score_certification_credibility(
    resume_text:    str,
    required_certs: list[str],
) -> float:
    """
    Score certifications considering:
    - Whether they're present
    - Whether they appear current (year mentioned)
    - Known certification value
    """
    if not required_certs:
        return 50.0

    text_lower = resume_text.lower()
    total_score = 0.0

    for cert in required_certs:
        cert_lower = cert.lower()
        if cert_lower not in text_lower:
            continue  # not found

        # Base score for having the cert
        base = 70.0

        # Check if a recent year is mentioned near the cert
        pattern = re.compile(
            r'(?:' + re.escape(cert_lower) + r'.{0,50}(\d{4})|(\d{4}).{0,50}' + re.escape(cert_lower) + r')',
            re.IGNORECASE
        )
        years_near_cert = []
        for match in pattern.finditer(text_lower):
            y = int(match.group(1) or match.group(2))
            if 2000 <= y <= CURRENT_YEAR:
                years_near_cert.append(y)

        if years_near_cert:
            most_recent = max(years_near_cert)
            validity    = CERT_VALIDITY.get(cert_lower, 3)
            age         = CURRENT_YEAR - most_recent
            if validity == 0 or age <= validity:
                base = 100.0  # current
            else:
                base = 50.0   # possibly expired

        total_score += base

    return round(total_score / len(required_certs), 2)


# ── 10. Red Flags Detection ───────────────────────────────────────────────────

def detect_red_flags(text: str) -> dict:
    """
    Detect potential red flags in resume:
    - Very short tenures (< 6 months)
    - Long unexplained gaps
    - Inconsistent career path
    - Exaggerated claims
    """
    flags    = []
    penalty  = 0

    # Short tenures — look for date ranges less than 6 months apart
    date_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|\bpresent\b|\bcurrent\b)'
    tenures = []
    for match in re.finditer(date_pattern, text.lower()):
        start = int(match.group(1))
        end   = CURRENT_YEAR if match.group(2) in ("present", "current") else int(match.group(2))
        if 1990 <= start <= CURRENT_YEAR and end >= start:
            tenures.append((start, end))

    short_tenures = [(s, e) for s, e in tenures if (e - s) == 0]
    if len(short_tenures) >= 2:
        flags.append("Multiple very short tenures detected")
        penalty += 10

    # Exaggerated claims
    exaggeration_patterns = [
        r'\b(?:expert|guru|ninja|rockstar|wizard)\s+in\b',
        r'\bproficient\s+in\s+(?:all|every|most)\b',
        r'\b\d{3,}\s+(?:programming\s+)?languages?\b',
    ]
    for pattern in exaggeration_patterns:
        if re.search(pattern, text.lower()):
            flags.append("Potentially exaggerated claims")
            penalty += 5
            break

    # Very long resume (possible padding)
    word_count = len(text.split())
    if word_count > 2000:
        flags.append("Unusually long resume — possible padding")
        penalty += 5

    return {
        "flags":   flags,
        "penalty": min(penalty, 25),  # max 25 point penalty
        "count":   len(flags),
    }


# ── Final Intelligent Score ───────────────────────────────────────────────────

@dataclass
class IntelligentScoringResult:
    # Core scores (0-100)
    semantic_score:         float = 0.0
    skills_score:           float = 0.0
    experience_score:       float = 0.0
    education_score:        float = 0.0
    certification_score:    float = 0.0

    # Advanced scores (0-100)
    career_progression:     float = 0.0
    skill_recency:          float = 0.0
    resume_quality:         float = 0.0
    job_title_relevance:    float = 0.0
    industry_match:         float = 0.0
    education_field:        float = 0.0

    # Final
    final_score:            float = 0.0
    red_flags:              list  = field(default_factory=list)
    red_flag_penalty:       float = 0.0
    is_overqualified:       bool  = False
    overqualification_ratio: float | None = None

    # Details
    matched_skills:         list[str] = field(default_factory=list)
    missing_skills:         list[str] = field(default_factory=list)
    matched_certs:          list[str] = field(default_factory=list)
    missing_certs:          list[str] = field(default_factory=list)
    contextual_skills:      list[str] = field(default_factory=list)
    inferred_skills:        list[str] = field(default_factory=list)
    experience_years_found: float     = 0.0
    education_level_found:  str       = ""
    resume_domain:          str       = ""
    job_domain:             str       = ""
    recommendation:         str       = ""


def get_recommendation(score: float) -> str:
    if score >= 80:  return "Highly Recommended"
    if score >= 65:  return "Strongly Consider"
    if score >= 45:  return "Consider"
    if score >= 30:  return "Weak Match"
    return "Not Recommended"


def compute_intelligent_score(
    resume_text:         str,
    resume_skills:       list[str],
    semantic_score:      float,
    job_required_skills: list[str],
    job_required_certs:  list[str],
    job_min_experience:  int | None,
    job_education_level: str | None,
    job_title:           str = "",
    job_text:            str = "",
) -> IntelligentScoringResult:
    from skills_matcher import advanced_skills_match
    from contextual_extractor import extract_contextual_skills as extract_contextual_skills_v2
    from composite_scorer import (
        skills_match_with_synonyms, score_experience_domain_aware,
        extract_education_level, score_education,
        score_certifications, extract_relevant_sections,
        detect_overqualification,
    )
    from experience_extractor import extract_years_of_experience

    # ── Core scores ───────────────────────────────────────────────────────────
    relevant_text = extract_relevant_sections(resume_text)

    # Domain-penalized semantic score
    # If resume and job are in different domains, penalize semantic score
    # because SBERT sees general professional language overlap
    resume_ind = detect_industry(resume_text)
    job_ind    = detect_industry(job_text)

    if resume_ind != job_ind and job_ind != "general" and resume_ind != "general":
        # Different domains — strong penalty
        sem_score = round(min(semantic_score, 50.0) * 0.70, 2)
    elif resume_ind != job_ind:
        # One is general — lighter penalty
        sem_score = round(semantic_score * 0.80, 2)
    else:
        # Same domain
        sem_score = round(semantic_score, 2)

    # Experience-based semantic penalty
    # Fresh graduates with theoretical knowledge shouldn't score
    # same as experienced professionals semantically
    exp_years_check = extract_years_of_experience(resume_text)
    if exp_years_check == 0:
        # No experience — cap semantic at 60%
        sem_score = round(min(sem_score, 60.0), 2)
    elif exp_years_check < 1:
        # Less than 1 year — cap at 70%
        sem_score = round(min(sem_score, 70.0), 2)

    # Advanced skills matching with partial credit
    adv_match      = advanced_skills_match(resume_skills, job_required_skills)
    base_skills_sc = round(adv_match["match_score"], 2)

    # Pull semantic score down if skills don't match within same domain
    # A resume with 0 matching skills shouldn't score 75% semantically
    if resume_ind == job_ind and base_skills_sc < 30:
        skill_penalty = (30 - base_skills_sc) * 0.4
        sem_score = round(max(sem_score - skill_penalty, 20.0), 2)
    # Also keep synonym-based for backward compat
    skills_result  = {
        "matched":       adv_match["matched"],
        "missing":       adv_match["missing"],
        "match_ratio":   adv_match["match_score"] / 100,
    }

    # Experience — only meaningful if candidate has relevant skills
    # If skills score is 0, experience is irrelevant to this job
    raw_exp_score = score_experience_domain_aware(resume_text, job_min_experience, job_text)
    exp_years     = extract_years_of_experience(resume_text)

    if base_skills_sc == 0:
        # No relevant skills at all — experience counts nothing
        exp_score = 0.0
    elif base_skills_sc < 30:
        # Very few skills — experience heavily discounted
        exp_score = round(raw_exp_score * (base_skills_sc / 100), 2)
    else:
        # Has relevant skills — experience counts normally
        exp_score = raw_exp_score

    overqual_info = detect_overqualification(exp_years, job_min_experience)

    # Education
    edu_name, _ = extract_education_level(resume_text)
    edu_score   = score_education(resume_text, job_education_level)

    # Certifications (credibility-aware)
    cert_cred_score = score_certification_credibility(resume_text, job_required_certs)
    _, matched_certs, missing_certs = score_certifications(
        resume_text, resume_skills, job_required_certs
    )

    # ── Advanced scores ───────────────────────────────────────────────────────

    # 1. Contextual skills — use improved extractor
    ctx_skills     = extract_contextual_skills_v2(resume_text)
    all_skills     = list(set(resume_skills + ctx_skills))
    skills_result2 = skills_match_with_synonyms(all_skills, job_required_skills)
    ctx_skills_sc  = round(skills_result2["match_ratio"] * 100, 2)

    # Contextual skills boost is limited when experience is very low
    if exp_years is not None and exp_years < 2:
        ctx_boost = ctx_skills_sc - base_skills_sc
        if ctx_boost > 15:
            ctx_skills_sc = base_skills_sc + 15  # cap contextual boost at 15%
    elif exp_years is not None and exp_years < 3:
        ctx_boost = ctx_skills_sc - base_skills_sc
        if ctx_boost > 25:
            ctx_skills_sc = base_skills_sc + 25  # cap contextual boost at 25%

    # 2. Career progression — penalize if no real work experience found
    career_score = score_career_progression(resume_text)
    if exp_years == 0:
        # Fresh graduate — career progression irrelevant
        career_score = min(career_score, 20.0)
    elif exp_years < 1:
        # Less than 1 year — heavily discounted
        career_score = min(career_score, 35.0)

    # 3. Skill recency
    recency_score = score_skills_with_recency(
        resume_text, skills_result["matched"], job_required_skills
    )

    # 4. Inferred skills
    inferred = infer_implicit_skills(all_skills)

    # 5. Resume quality
    quality_score = score_resume_quality(resume_text)

    # 6. Job title relevance
    title_score = score_job_title_relevance(resume_text, job_title)

    # 7. Industry match
    industry_score = score_industry_match(resume_text, job_text)

    # 8. Education field
    edu_field_score = score_education_field(resume_text, job_text)

    # 9. Red flags
    red_flag_result = detect_red_flags(resume_text)
    penalty         = red_flag_result["penalty"]

    # ── Context-enhanced skills score ─────────────────────────────────────────
    final_skills = max(base_skills_sc, ctx_skills_sc)

    # Academic skills discount — if no work experience, skills likely theoretical
    # A fresh graduate with all required skills on paper still lacks practical experience
    if exp_years == 0 and final_skills > 50:
        # Cap skills at 55% for candidates with zero work experience
        final_skills = min(final_skills, 55.0)
    elif exp_years is not None and exp_years < 1 and final_skills > 60:
        final_skills = min(final_skills, 60.0)
    elif exp_years is not None and exp_years < 2 and final_skills > 70:
        final_skills = min(final_skills, 70.0)

    # ── Domain gate — penalize domain-dependent scores when skills = 0 ────────
    # Skills gate factor: 0.0 when no skills, 1.0 when full skills match
    skills_gate = final_skills / 100.0

    # Education: neutral (50) when no requirement, but gated by domain match
    # If wrong domain and no skills, education in wrong field is not relevant
    if final_skills == 0 and industry_score < 50:
        edu_score      = min(edu_score, 20.0)      # wrong domain, no skills
        career_score   = min(career_score, 15.0)   # career in wrong field irrelevant
        edu_field_score = min(edu_field_score, 20.0)
    elif final_skills < 30 and industry_score < 50:
        edu_score      = round(edu_score * 0.4, 2)
        career_score   = round(career_score * 0.3, 2)
        edu_field_score = round(edu_field_score * 0.4, 2)

    # Recency is 0 if no skills matched
    if final_skills == 0:
        recency_score = 0.0

    # Job title relevance gated by skills
    title_score = round(title_score * skills_gate, 2)

    # ── Weighted final score ──────────────────────────────────────────────────
    raw_score = (
        0.25 * sem_score        +   # semantic similarity
        0.20 * final_skills     +   # skills match (context-enhanced)
        0.10 * exp_score        +   # experience relevance (skills-gated)
        0.08 * edu_score        +   # education level (domain-gated)
        0.07 * cert_cred_score  +   # certification credibility
        0.07 * career_score     +   # career progression (domain-gated)
        0.07 * recency_score    +   # skill recency (skills-gated)
        0.06 * quality_score    +   # resume quality
        0.05 * title_score      +   # job title relevance (skills-gated)
        0.03 * industry_score   +   # industry match
        0.02 * edu_field_score      # education field (domain-gated)
    )

    final = max(round(raw_score - penalty, 2), 0)

    return IntelligentScoringResult(
        semantic_score         = sem_score,
        skills_score           = final_skills,
        experience_score       = round(exp_score, 2),
        education_score        = round(edu_score, 2),
        certification_score    = cert_cred_score,
        career_progression     = round(career_score, 2),
        skill_recency          = round(recency_score, 2),
        resume_quality         = round(quality_score, 2),
        job_title_relevance    = round(title_score, 2),
        industry_match         = round(industry_score, 2),
        education_field        = round(edu_field_score, 2),
        final_score            = final,
        red_flags              = red_flag_result["flags"],
        red_flag_penalty       = penalty,
        is_overqualified        = overqual_info["is_overqualified"],
        overqualification_ratio = overqual_info["ratio"],
        matched_skills         = (
                                   adv_match["matched"] +
                                   [f"{s}" for s in adv_match.get("adjacent", [])] +
                                   [f"{s}" for s in adv_match.get("partial_matches", [])]
                               ),
        missing_skills         = adv_match["missing"],
        matched_certs          = matched_certs,
        missing_certs          = missing_certs,
        contextual_skills      = ctx_skills,
        inferred_skills        = inferred,
        experience_years_found = exp_years,
        education_level_found  = edu_name,
        resume_domain          = detect_industry(resume_text),
        job_domain             = detect_industry(job_text),
        recommendation         = get_recommendation(final),
    )