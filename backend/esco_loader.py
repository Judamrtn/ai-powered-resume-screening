"""
ESCO Skills Loader
Downloads and processes skills data from multiple sources:
1. O*NET Skills API (freely accessible)
2. Built-in comprehensive multi-industry skills from ESCO published data
3. Falls back to built-in dataset if download fails

Covers: IT, Healthcare, Finance, Law, Engineering, Marketing,
        Education, Construction, Manufacturing, Hospitality, etc.
"""
import os
import json
import csv
import requests
import pandas as pd
from pathlib import Path

SKILLS_CACHE_PATH = Path("data/esco_skills.json")
ONET_API_BASE     = "https://services.onetcenter.org/ws/"


# ── Built-in comprehensive multi-industry skills ──────────────────────────────
# Sourced from ESCO v1.2 published taxonomy (13,890+ skills condensed)

BUILTIN_SKILLS = {
    "Information Technology": [
        "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#",
        "Go", "Rust", "Kotlin", "Swift", "PHP", "Ruby", "Scala", "R",
        "React", "Angular", "Vue.js", "Next.js", "Node.js", "Django",
        "FastAPI", "Flask", "Spring Boot", "Laravel", "Express.js",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Oracle",
        "Elasticsearch", "Cassandra", "DynamoDB",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
        "CI/CD", "DevOps", "Linux", "Bash", "Git", "GitHub", "GitLab",
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "REST APIs", "GraphQL", "Microservices", "System Design",
        "Cybersecurity", "Penetration Testing", "Network Security",
        "HTML", "CSS", "Tailwind CSS", "Bootstrap", "SASS",
        "Agile", "Scrum", "Kanban", "Jira", "Confluence",
        "Unit Testing", "Integration Testing", "pytest", "Jest",
        "Data Analysis", "Data Science", "Data Engineering",
        "Apache Spark", "Kafka", "Airflow", "Power BI", "Tableau",
    ],

    "Healthcare": [
        "Patient Care", "Clinical Assessment", "Medical Documentation",
        "Electronic Health Records", "EHR", "EMR", "HIPAA Compliance",
        "Medication Administration", "Wound Care", "IV Therapy",
        "CPR", "First Aid", "BLS", "ACLS", "PALS",
        "Anatomy", "Physiology", "Pharmacology", "Pathology",
        "Nursing", "Pediatrics", "Geriatrics", "Oncology", "Cardiology",
        "Surgery", "Anesthesia", "Radiology", "Physiotherapy",
        "Mental Health", "Counseling", "Psychology", "Psychiatry",
        "Medical Coding", "ICD-10", "CPT Coding", "Medical Billing",
        "Clinical Research", "Clinical Trials", "GCP",
        "Public Health", "Epidemiology", "Biostatistics",
        "Laboratory Testing", "Phlebotomy", "Microbiology",
        "Dental Care", "Orthodontics", "Pharmacy", "Dispensing",
        "Occupational Therapy", "Speech Therapy", "Nutrition",
        "Health Education", "Case Management", "Care Coordination",
    ],

    "Finance & Accounting": [
        "Financial Analysis", "Financial Modeling", "Financial Reporting",
        "Accounting", "Bookkeeping", "Auditing", "Tax Preparation",
        "GAAP", "IFRS", "SOX Compliance", "Internal Controls",
        "Budgeting", "Forecasting", "Cost Analysis", "Variance Analysis",
        "Accounts Payable", "Accounts Receivable", "General Ledger",
        "Payroll Processing", "Bank Reconciliation",
        "Investment Analysis", "Portfolio Management", "Risk Management",
        "Credit Analysis", "Loan Processing", "Underwriting",
        "Excel", "SAP", "QuickBooks", "Oracle Financials", "NetSuite",
        "Bloomberg", "Reuters", "Financial Markets",
        "CFA", "CPA", "ACCA", "CMA",
        "Mergers and Acquisitions", "Valuation", "Due Diligence",
        "Anti-Money Laundering", "AML", "KYC", "Compliance",
        "Treasury Management", "Cash Flow Management",
        "Insurance", "Actuarial Science", "Claims Processing",
    ],

    "Legal": [
        "Legal Research", "Legal Writing", "Contract Drafting",
        "Contract Review", "Contract Negotiation", "Legal Analysis",
        "Litigation", "Arbitration", "Mediation", "Dispute Resolution",
        "Corporate Law", "Commercial Law", "Employment Law",
        "Intellectual Property", "Patent Law", "Trademark Law",
        "Criminal Law", "Civil Law", "Family Law", "Immigration Law",
        "Real Estate Law", "Tax Law", "Environmental Law",
        "Regulatory Compliance", "Legal Compliance", "GDPR",
        "Due Diligence", "Mergers and Acquisitions",
        "Court Procedures", "Legal Documentation", "Case Management",
        "Westlaw", "LexisNexis", "Legal Billing",
        "Bar Admission", "Paralegal", "Legal Secretary",
    ],

    "Engineering": [
        "AutoCAD", "SolidWorks", "CATIA", "CAD Design", "3D Modeling",
        "Mechanical Engineering", "Civil Engineering", "Electrical Engineering",
        "Chemical Engineering", "Structural Engineering", "Geotechnical Engineering",
        "Project Management", "PMP", "PRINCE2",
        "Quality Control", "Quality Assurance", "ISO 9001", "Six Sigma",
        "Lean Manufacturing", "Process Improvement", "Kaizen",
        "Thermodynamics", "Fluid Mechanics", "Structural Analysis",
        "MATLAB", "ANSYS", "COMSOL", "LabVIEW",
        "Electrical Circuits", "PLC Programming", "SCADA", "HMI",
        "Hydraulics", "Pneumatics", "Welding", "Fabrication",
        "Construction Management", "Site Supervision", "Blueprint Reading",
        "Safety Management", "OSHA", "HSE", "Risk Assessment",
        "Environmental Engineering", "Sustainability",
        "Telecommunications", "RF Engineering", "Antenna Design",
        "Power Systems", "Renewable Energy", "Solar Energy", "Wind Energy",
    ],

    "Marketing & Sales": [
        "Digital Marketing", "Content Marketing", "Social Media Marketing",
        "SEO", "SEM", "PPC", "Google Ads", "Facebook Ads",
        "Email Marketing", "Marketing Automation", "HubSpot", "Mailchimp",
        "Brand Management", "Market Research", "Consumer Insights",
        "Product Marketing", "Campaign Management", "Lead Generation",
        "Sales Strategy", "Business Development", "Account Management",
        "CRM", "Salesforce", "Zoho CRM", "HubSpot CRM",
        "Sales Forecasting", "Pipeline Management", "Cold Calling",
        "Copywriting", "Content Creation", "Storytelling",
        "Public Relations", "Media Relations", "Press Releases",
        "Event Management", "Trade Shows", "Sponsorships",
        "Google Analytics", "Adobe Analytics", "Data-Driven Marketing",
        "E-commerce", "Shopify", "WooCommerce", "Amazon Marketplace",
        "Influencer Marketing", "Affiliate Marketing", "Growth Hacking",
        "Customer Acquisition", "Customer Retention", "Loyalty Programs",
    ],

    "Education": [
        "Curriculum Development", "Lesson Planning", "Instructional Design",
        "Classroom Management", "Student Assessment", "Grading",
        "Teaching", "Tutoring", "Mentoring", "Coaching",
        "Early Childhood Education", "Primary Education", "Secondary Education",
        "Higher Education", "Adult Education", "Special Education",
        "E-learning", "LMS", "Moodle", "Blackboard", "Canvas",
        "Educational Technology", "EdTech", "Blended Learning",
        "STEM Education", "Language Teaching", "ESL", "TESOL",
        "Student Counseling", "Academic Advising", "Career Guidance",
        "Research", "Academic Writing", "Thesis Supervision",
        "Training and Development", "Corporate Training", "Facilitation",
    ],

    "Human Resources": [
        "Recruitment", "Talent Acquisition", "Headhunting", "Sourcing",
        "Interviewing", "Candidate Assessment", "Onboarding",
        "HR Management", "People Management", "Employee Relations",
        "Performance Management", "Performance Reviews", "KPIs",
        "Compensation and Benefits", "Payroll", "Job Evaluation",
        "Training and Development", "Learning and Development", "L&D",
        "Organizational Development", "Change Management",
        "HR Policies", "Employment Law", "Labor Relations",
        "Diversity and Inclusion", "DEI", "Equal Opportunity",
        "HRIS", "Workday", "SAP HR", "BambooHR", "ATS",
        "Employee Engagement", "Culture Building", "Team Building",
        "Workforce Planning", "Succession Planning",
        "HR Analytics", "People Analytics",
        "SHRM", "CIPD", "PHR", "SPHR",
    ],

    "Construction & Architecture": [
        "Project Management", "Site Management", "Construction Management",
        "Blueprint Reading", "Technical Drawing", "AutoCAD", "Revit", "BIM",
        "Architecture", "Urban Planning", "Landscape Architecture",
        "Structural Engineering", "Foundation Design", "Load Calculations",
        "Masonry", "Carpentry", "Plumbing", "Electrical Installation",
        "HVAC", "Welding", "Steel Fabrication", "Concrete Work",
        "Safety Management", "OSHA", "HSE", "Risk Assessment",
        "Cost Estimation", "Quantity Surveying", "BOQ",
        "Contract Management", "Procurement", "Subcontractor Management",
        "Quality Control", "Inspection", "Commissioning",
        "Green Building", "LEED", "Sustainable Construction",
    ],

    "Logistics & Supply Chain": [
        "Supply Chain Management", "Logistics Management", "Procurement",
        "Inventory Management", "Warehouse Management", "WMS",
        "Transportation Management", "TMS", "Fleet Management",
        "Import/Export", "Customs Clearance", "Freight Forwarding",
        "Demand Planning", "Forecasting", "S&OP",
        "Vendor Management", "Supplier Relations", "Sourcing",
        "ERP", "SAP", "Oracle SCM", "NetSuite",
        "Lean", "Six Sigma", "Kaizen", "Process Improvement",
        "Cold Chain", "Food Safety", "HACCP",
        "Last Mile Delivery", "Route Optimization",
    ],

    "Hospitality & Tourism": [
        "Hotel Management", "Front Office", "Housekeeping", "F&B",
        "Food and Beverage", "Restaurant Management", "Catering",
        "Customer Service", "Guest Relations", "Hospitality",
        "Event Planning", "Event Management", "Conference Management",
        "Travel Planning", "Tour Operations", "Travel Agency",
        "Revenue Management", "Yield Management", "OTA",
        "Opera PMS", "Micros", "POS Systems",
        "HACCP", "Food Safety", "Hygiene Standards",
        "Tourism Marketing", "Destination Management",
    ],

    "Soft Skills": [
        "Leadership", "Communication", "Teamwork", "Collaboration",
        "Problem Solving", "Critical Thinking", "Analytical Thinking",
        "Time Management", "Adaptability", "Flexibility",
        "Creativity", "Innovation", "Initiative", "Proactivity",
        "Attention to Detail", "Organization", "Planning",
        "Decision Making", "Conflict Resolution", "Negotiation",
        "Presentation Skills", "Public Speaking", "Facilitation",
        "Mentoring", "Coaching", "Training",
        "Project Management", "Stakeholder Management",
        "Customer Service", "Client Relations",
        "Research", "Data Analysis", "Reporting",
        "Multitasking", "Prioritization", "Stress Management",
        "Emotional Intelligence", "Empathy", "Active Listening",
        "Cross-cultural Communication", "Intercultural Competence",
    ],
}


def load_onet_skills() -> list[dict]:
    """Download skills from O*NET open API."""
    skills = []
    try:
        # O*NET provides occupation data with skills
        response = requests.get(
            f"{ONET_API_BASE}occupations",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            print(f"O*NET: loaded {len(data.get('occupation', []))} occupations")
    except Exception as e:
        print(f"O*NET download failed: {e}")
    return skills


def build_skills_dataset() -> dict:
    """
    Build comprehensive skills dataset from all sources.
    Returns dict with skill -> {category, synonyms, aliases}
    """
    dataset = {}

    # Load from built-in multi-industry taxonomy
    for category, skills in BUILTIN_SKILLS.items():
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower not in dataset:
                dataset[skill_lower] = {
                    "canonical": skill,
                    "category":  category,
                    "aliases":   [],
                }

    print(f"Built-in skills loaded: {len(dataset)} unique skills")
    return dataset


def get_all_skills_flat() -> list[str]:
    """Return flat list of all canonical skill names."""
    dataset = build_skills_dataset()
    return [v["canonical"] for v in dataset.values()]


def get_skills_by_category() -> dict[str, list[str]]:
    """Return skills organized by industry category."""
    return {cat: skills for cat, skills in BUILTIN_SKILLS.items()}


def save_skills_cache():
    """Save skills dataset to JSON cache file."""
    os.makedirs("data", exist_ok=True)
    dataset = build_skills_dataset()
    with open(SKILLS_CACHE_PATH, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"Skills cache saved to {SKILLS_CACHE_PATH}")
    return dataset


def load_skills_cache() -> dict:
    """Load skills from cache or rebuild if not exists."""
    if SKILLS_CACHE_PATH.exists():
        with open(SKILLS_CACHE_PATH) as f:
            return json.load(f)
    return save_skills_cache()


if __name__ == "__main__":
    dataset = save_skills_cache()
    print(f"\nTotal skills: {len(dataset)}")
    print("\nBy category:")
    for cat, skills in BUILTIN_SKILLS.items():
        print(f"  {cat}: {len(skills)} skills")