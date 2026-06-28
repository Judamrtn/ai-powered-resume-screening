# â”€â”€ Skills Taxonomy & Synonym Map â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Maps aliases/abbreviations to canonical skill names.
# Add new entries here as the job market evolves.

SKILL_SYNONYMS: dict[str, str] = {
    # JavaScript ecosystem
    "js":               "JavaScript",
    "javascript":       "JavaScript",
    "typescript":       "TypeScript",
    "ts":               "TypeScript",
    "node":             "Node.js",
    "nodejs":           "Node.js",
    "node.js":          "Node.js",
    "react":            "React",
    "reactjs":          "React",
    "react.js":         "React",
    "vue":              "Vue.js",
    "vuejs":            "Vue.js",
    "angular":          "Angular",
    "angularjs":        "Angular",
    "next":             "Next.js",
    "nextjs":           "Next.js",

    # Python ecosystem
    "python":           "Python",
    "py":               "Python",
    "fastapi":          "FastAPI",
    "django":           "Django",
    "flask":            "Flask",
    "pandas":           "Pandas",
    "numpy":            "NumPy",
    "sklearn":          "Scikit-learn",
    "scikit-learn":     "Scikit-learn",
    "scikit learn":     "Scikit-learn",
    "tensorflow":       "TensorFlow",
    "tf":               "TensorFlow",
    "pytorch":          "PyTorch",
    "torch":            "PyTorch",

    # ML / AI
    "ml":               "Machine Learning",
    "machine learning": "Machine Learning",
    "dl":               "Deep Learning",
    "deep learning":    "Deep Learning",
    "ai":               "Artificial Intelligence",
    "nlp":              "Natural Language Processing",
    "natural language processing": "Natural Language Processing",
    "cv":               "Computer Vision",
    "computer vision":  "Computer Vision",
    "llm":              "Large Language Models",
    "rl":               "Reinforcement Learning",

    # Databases
    "postgres":         "PostgreSQL",
    "postgresql":       "PostgreSQL",
    "mysql":            "MySQL",
    "mongo":            "MongoDB",
    "mongodb":          "MongoDB",
    "redis":            "Redis",
    "sqlite":           "SQLite",
    "mssql":            "SQL Server",
    "sql server":       "SQL Server",
    "oracle db":        "Oracle",
    "elasticsearch":    "Elasticsearch",
    "elastic":          "Elasticsearch",

    # Cloud
    "aws":              "AWS",
    "amazon web services": "AWS",
    "gcp":              "GCP",
    "google cloud":     "GCP",
    "azure":            "Azure",
    "microsoft azure":  "Azure",

    # DevOps / Infrastructure
    "docker":           "Docker",
    "k8s":              "Kubernetes",
    "kubernetes":       "Kubernetes",
    "terraform":        "Terraform",
    "ci/cd":            "CI/CD",
    "cicd":             "CI/CD",
    "github actions":   "GitHub Actions",
    "jenkins":          "Jenkins",
    "ansible":          "Ansible",
    "linux":            "Linux",
    "unix":             "Linux",
    "bash":             "Bash",
    "shell":            "Bash",
    "shell scripting":  "Bash",

    # Networking
    "networking":       "Networking",
    "tcp/ip":           "TCP/IP",
    "tcp ip":           "TCP/IP",
    "cisco":            "Cisco",
    "ccna":             "CCNA",
    "ccnp":             "CCNP",
    "firewall":         "Firewall",
    "vpn":              "VPN",

    # Languages
    "java":             "Java",
    "c++":              "C++",
    "cpp":              "C++",
    "c#":               "C#",
    "csharp":           "C#",
    "go":               "Go",
    "golang":           "Go",
    "rust":             "Rust",
    "kotlin":           "Kotlin",
    "swift":            "Swift",
    "php":              "PHP",
    "ruby":             "Ruby",
    "scala":            "Scala",
    "r":                "R",

    # APIs / Architecture
    "rest":             "REST APIs",
    "rest api":         "REST APIs",
    "restful":          "REST APIs",
    "graphql":          "GraphQL",
    "grpc":             "gRPC",
    "microservices":    "Microservices",
    "api":              "REST APIs",

    # Tools
    "git":              "Git",
    "github":           "GitHub",
    "gitlab":           "GitLab",
    "jira":             "Jira",
    "postman":          "Postman",
    "figma":            "Figma",

    # HR synonyms
    "sourcing":                    "Recruitment",
    "talent sourcing":             "Recruitment",
    "headhunting":                 "Recruitment",
    "talent acquisition":          "Recruitment",
    "hiring":                      "Recruitment",
    "staffing":                    "Recruitment",
    "employee engagement":         "Employee Relations",
    "staff relations":             "Employee Relations",
    "workplace relations":         "Employee Relations",
    "performance appraisal":       "Performance Management",
    "performance review":          "Performance Management",
    "performance evaluation":      "Performance Management",
    "kpi management":              "Performance Management",
    "hr policy":                   "HR Policies",
    "hr procedures":               "HR Policies",
    "people policies":             "HR Policies",
    "induction":                   "Onboarding",
    "new hire orientation":        "Onboarding",
    "employee onboarding":         "Onboarding",
    "learning and development":    "Training",
    "l&d":                         "Training",
    "staff training":              "Training",
    "compensation":                "Payroll",
    "benefits administration":     "Payroll",
    "remuneration":                "Payroll",

    # Finance synonyms
    "bookkeeping":                 "Accounting",
    "accounts":                    "Accounting",
    "p&l":                         "Financial Analysis",
    "profit and loss":             "Financial Analysis",
    "financial modelling":         "Financial Modeling",
    "budgeting":                   "Budget Management",
    "cost management":             "Cost Analysis",
    "variance analysis":           "Financial Analysis",
    "ifrs":                        "Accounting",
    "gaap":                        "Accounting",

    # Marketing synonyms
    "digital advertising":         "Digital Marketing",
    "online marketing":            "Digital Marketing",
    "search engine optimization":  "SEO",
    "search engine marketing":     "SEM",
    "pay per click":               "PPC",
    "content strategy":            "Content Marketing",
    "brand strategy":              "Brand Management",
    "market analysis":             "Market Research",
    "crm management":              "CRM",

    # Healthcare synonyms
    "patient management":          "Patient Care",
    "clinical care":               "Patient Care",
    "bedside manner":              "Patient Care",
    "drug administration":         "Medication Administration",
    "clinical documentation":      "Medical Documentation",
    "ehr":                         "Electronic Health Records",
    "emr":                         "Electronic Health Records",
    "basic life support":          "BLS",
    "advanced cardiac life support": "ACLS",

    # Legal synonyms
    "contract management":         "Contract Drafting",
    "legal drafting":              "Legal Writing",
    "dispute resolution":          "Litigation",
    "regulatory affairs":         "Regulatory Compliance",
    "gdpr compliance":             "GDPR",
    "due diligence":               "Legal Research",

    # Engineering synonyms
    "cad":                         "AutoCAD",
    "computer aided design":       "AutoCAD",
    "3d design":                   "3D Modeling",
    "quality assurance":           "Quality Control",
    "qa":                          "Quality Control",
    "qc":                          "Quality Control",
    "lean six sigma":              "Six Sigma",
    "project delivery":            "Project Management",
    "hse":                         "Safety Management",
    "health and safety":           "Safety Management",

    # Soft skills
    "communication":    "Communication",
    "teamwork":         "Teamwork",
    "leadership":       "Leadership",
    "problem solving":  "Problem Solving",
    "problem-solving":  "Problem Solving",
    "agile":            "Agile",
    "scrum":            "Scrum",
}


def normalize_skill(skill: str) -> str:
    """Return canonical form of a skill, or title-cased original if not in taxonomy."""
    return SKILL_SYNONYMS.get(skill.lower().strip(), skill.strip())


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize a list of skills to canonical forms, removing duplicates."""
    seen = set()
    result = []
    for skill in skills:
        canonical = normalize_skill(skill)
        if canonical.lower() not in seen:
            seen.add(canonical.lower())
            result.append(canonical)
    return result


def skills_match_with_synonyms(resume_skills: list[str], job_skills: list[str], resume_text: str = "") -> dict:
    import re
    normalized_resume = {normalize_skill(s).lower() for s in resume_skills}
    normalized_job    = [(s, normalize_skill(s)) for s in job_skills]
    matched = []
    missing = []
    for orig, norm in normalized_job:
        if norm.lower() in normalized_resume:
            matched.append(orig)
        elif resume_text:
            pattern = r'(?<![A-Za-z0-9])' + re.escape(orig) + r'(?![A-Za-z0-9])'
            if re.search(pattern, resume_text, re.IGNORECASE):
                matched.append(orig)
            else:
                missing.append(orig)
        else:
            missing.append(orig)
    ratio = len(matched) / len(job_skills) if job_skills else 0.0
    return {
        "matched":        matched,
        "missing":        missing,
        "match_ratio":    ratio,
        "matched_count":  len(matched),
        "total_required": len(job_skills),
    }
   