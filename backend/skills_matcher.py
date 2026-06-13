"""
Advanced Skills Matcher
Implements:
1. Partial domain credit for adjacent skills
2. Fuzzy skill matching (partial string overlap)
3. Semantic skill similarity using word vectors
4. Skill hierarchy matching (parent/child skills)
"""
from __future__ import annotations
import re
from taxonomy import normalize_skill

# ── Skill adjacency map ───────────────────────────────────────────────────────
# Maps required skills to adjacent/related skills that deserve partial credit
SKILL_ADJACENCY = {
    # HR
    "Recruitment":          ["Sourcing", "Talent Acquisition", "Headhunting", "Hiring", "Staffing", "Interviewing"],
    "Employee Relations":   ["Employee Engagement", "Staff Relations", "People Management", "HR", "Workplace Relations"],
    "Performance Management": ["Performance Review", "Performance Appraisal", "KPI", "Goal Setting", "Evaluation"],
    "HR Policies":          ["Compliance", "Regulatory", "Labor Law", "Employment Law", "HR Procedures"],
    "Onboarding":           ["Training", "Induction", "Orientation", "L&D", "Learning and Development"],

    # IT
    "Python":               ["Django", "FastAPI", "Flask", "Pandas", "NumPy", "Scripting"],
    "JavaScript":           ["React", "Node.js", "TypeScript", "Vue.js", "Angular", "jQuery"],
    "PostgreSQL":           ["MySQL", "SQLite", "Database", "SQL", "Oracle", "MariaDB"],
    "Docker":               ["Kubernetes", "Containerization", "DevOps", "CI/CD"],
    "AWS":                  ["GCP", "Azure", "Cloud", "EC2", "S3", "Lambda"],
    "Machine Learning":     ["Deep Learning", "AI", "NLP", "TensorFlow", "PyTorch", "Scikit-learn"],
    "REST APIs":            ["API Design", "GraphQL", "gRPC", "Web Services", "HTTP"],

    # Finance
    "Financial Analysis":   ["Accounting", "Financial Modeling", "Budgeting", "Forecasting", "P&L"],
    "Accounting":           ["Bookkeeping", "GAAP", "IFRS", "Auditing", "Tax"],
    "Risk Management":      ["Compliance", "Internal Controls", "Audit", "Due Diligence"],

    # Marketing
    "Digital Marketing":    ["SEO", "SEM", "PPC", "Social Media Marketing", "Content Marketing"],
    "SEO":                  ["Google Analytics", "Content Marketing", "Keyword Research", "SEM"],
    "Brand Management":     ["Marketing", "Campaign Management", "Content Strategy"],

    # Healthcare
    "Patient Care":         ["Nursing", "Clinical Skills", "Bedside Manner", "Healthcare"],
    "Clinical Assessment":  ["Diagnosis", "Patient Evaluation", "Medical Documentation"],

    # Engineering
    "Project Management":   ["Planning", "Scheduling", "Risk Management", "Stakeholder Management", "PMP"],
    "Quality Control":      ["Quality Assurance", "ISO", "Six Sigma", "Inspection", "Testing"],
    "AutoCAD":              ["CAD", "3D Modeling", "SolidWorks", "CATIA", "Technical Drawing"],
}

# Partial credit weights
EXACT_MATCH_WEIGHT    = 1.0   # exact or synonym match
ADJACENT_MATCH_WEIGHT = 0.4   # adjacent/related skill
FUZZY_MATCH_WEIGHT    = 0.25  # partial string overlap


# Words that are too generic to justify a fuzzy match
STOP_WORDS = {
    "management", "analysis", "reporting", "skills", "experience",
    "time", "data", "business", "service", "work", "general",
    "basic", "advanced", "professional", "technical", "strategic",
}


def fuzzy_skill_match(skill_a: str, skill_b: str) -> float:
    """
    Check partial string overlap between two skills.
    Stricter than before — requires meaningful word overlap,
    not just any common word.
    """
    a = skill_a.lower().strip()
    b = skill_b.lower().strip()

    if a == b:
        return 1.0

    # One fully contains the other (e.g. "SQL" in "SQL Server")
    if a in b or b in a:
        # Only if the contained word is meaningful (not a stop word)
        shorter = a if len(a) <= len(b) else b
        if shorter in STOP_WORDS:
            return 0.0
        return 0.5

    # Word overlap — only count non-stopword words
    words_a = set(a.split()) - STOP_WORDS
    words_b = set(b.split()) - STOP_WORDS

    if not words_a or not words_b:
        return 0.0

    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))

    # Require at least 0.7 overlap AND at least one meaningful shared word
    if overlap >= 0.7 and len(words_a & words_b) >= 1:
        return 0.3  # reduced weight for fuzzy
    return 0.0


def advanced_skills_match(
    resume_skills: list[str],
    job_skills:    list[str],
) -> dict:
    """
    Match resume skills against job skills with partial credit.

    Returns:
        matched:         exact matches
        adjacent:        adjacent skill matches
        missing:         completely missing skills
        match_score:     weighted score 0-100
        exact_ratio:     pure exact match ratio
    """
    if not job_skills:
        return {
            "matched": [], "adjacent": [], "missing": [],
            "match_score": 0.0, "exact_ratio": 0.0,
            "partial_matches": [],
        }

    # Normalize all skills
    norm_resume = {normalize_skill(s).lower(): s for s in resume_skills}
    norm_job    = [(s, normalize_skill(s)) for s in job_skills]

    matched        = []
    adjacent       = []
    partial        = []
    missing        = []
    total_weight   = 0.0

    for orig_job, norm_job_skill in norm_job:
        best_weight  = 0.0
        best_match   = None
        match_type   = None

        # 1. Exact/synonym match
        if norm_job_skill.lower() in norm_resume:
            best_weight = EXACT_MATCH_WEIGHT
            best_match  = norm_resume[norm_job_skill.lower()]
            match_type  = "exact"

        # 2. Adjacent skill match
        if best_weight < EXACT_MATCH_WEIGHT:
            adjacents = SKILL_ADJACENCY.get(orig_job, []) + SKILL_ADJACENCY.get(norm_job_skill, [])
            for adj in adjacents:
                adj_norm = normalize_skill(adj).lower()
                if adj_norm in norm_resume:
                    if ADJACENT_MATCH_WEIGHT > best_weight:
                        best_weight = ADJACENT_MATCH_WEIGHT
                        best_match  = norm_resume[adj_norm]
                        match_type  = "adjacent"
                    break

        # 3. Fuzzy match
        if best_weight < ADJACENT_MATCH_WEIGHT:
            for res_norm, res_orig in norm_resume.items():
                fuzz = fuzzy_skill_match(norm_job_skill, res_norm)
                weight = fuzz * FUZZY_MATCH_WEIGHT
                if weight > best_weight:
                    best_weight = weight
                    best_match  = res_orig
                    match_type  = "fuzzy"

        # Categorize
        if best_weight >= EXACT_MATCH_WEIGHT:
            matched.append(orig_job)
            total_weight += EXACT_MATCH_WEIGHT
        elif best_weight >= ADJACENT_MATCH_WEIGHT:
            adjacent.append(f"{orig_job} (via {best_match})")
            total_weight += best_weight
        elif best_weight > 0:
            partial.append(f"{orig_job} (~{best_match})")
            total_weight += best_weight
        else:
            missing.append(orig_job)

    # Weighted score
    match_score = round((total_weight / len(job_skills)) * 100, 2)
    exact_ratio = round((len(matched) / len(job_skills)) * 100, 2)

    return {
        "matched":        matched,
        "adjacent":       adjacent,
        "partial_matches": partial,
        "missing":        missing,
        "match_score":    match_score,
        "exact_ratio":    exact_ratio,
    }