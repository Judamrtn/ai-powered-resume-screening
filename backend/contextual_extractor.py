"""
Contextual Skills Extractor v2
Extracts skills implied by action phrases across all industries.
Patterns tested against real resume text.
"""
from __future__ import annotations
import re

CONTEXTUAL_PATTERNS = [
    # ── Finance & Accounting ───────────────────────────────────────────────
    (r'(?:prepared?|drafted?|produced?|compiled?)\s+(?:monthly|annual|quarterly|weekly)?\s*(?:financial\s+)?(?:statements?|reports?|accounts?)', ["Financial Reporting", "Accounting"]),
    (r'(?:analyzed?|analysed?|reviewed?)\s+(?:financial\s+)?(?:data|performance|results|trends?|figures?)', ["Financial Analysis"]),
    (r'(?:managed?|handled?|processed?|oversee|oversaw)\s+accounts?\s+(?:payable|receivable)', ["Accounting", "Bookkeeping"]),
    (r'(?:conducted?|performed?|carried?\s+out)\s+(?:internal\s+|external\s+)?audit', ["Auditing", "Compliance"]),
    (r'(?:developed?|monitored?|managed?|prepared?|created?)\s+(?:annual\s+|operational\s+)?budget', ["Budgeting", "Budget Management"]),
    (r'(?:processed?|administered?|managed?|ran?)\s+payroll', ["Payroll", "Accounting"]),
    (r'reconciled?\s+(?:bank\s+)?(?:statements?|accounts?|ledgers?)', ["Accounting", "Bank Reconciliation"]),
    (r'(?:filed?|prepared?|submitted?)\s+(?:corporate\s+|personal\s+)?tax', ["Tax Preparation", "Accounting"]),
    (r'(?:forecasted?|projected?|modeled?)\s+(?:revenue|costs?|expenses?|cash\s+flow)', ["Financial Forecasting", "Financial Modeling"]),
    (r'managed?\s+(?:a\s+)?budget\s+of\s+(?:\$|€|£|ugx|rwf)?\s*[\d,]+', ["Budget Management", "Financial Analysis"]),
    (r'(?:reduced?|cut|decreased?)\s+costs?\s+by\s+\d+', ["Cost Reduction", "Financial Analysis"]),
    (r'(?:increased?|grew?|improved?)\s+(?:revenue|profit|sales)\s+by\s+\d+', ["Revenue Growth", "Financial Analysis"]),
    (r'(?:managed?|maintained?)\s+(?:general\s+)?ledger', ["Accounting", "Bookkeeping"]),
    (r'(?:prepared?|filed?)\s+(?:vat|gst|tax)\s+(?:returns?|filings?)', ["Tax Preparation", "Compliance"]),

    # ── HR ─────────────────────────────────────────────────────────────────
    (r'(?:screened?|shortlisted?|interviewed?)\s+(?:candidates?|applicants?)', ["Recruitment", "Interviewing"]),
    (r'(?:posted?|advertised?|published?)\s+(?:job|vacancy|position|opening)', ["Recruitment"]),
    (r'(?:onboard(?:ed|ing)?|orient(?:ed|ing)?)\s+(?:new\s+)?(?:employees?|staff|hires?)', ["Onboarding"]),
    (r'(?:conducted?|carried?\s+out|facilitated?)\s+(?:performance\s+)?(?:reviews?|appraisals?|evaluations?)', ["Performance Management"]),
    (r'(?:developed?|drafted?|created?|implemented?)\s+(?:hr\s+)?(?:policies|procedures|guidelines|handbook)', ["HR Policies"]),
    (r'(?:resolved?|handled?|managed?|addressed?)\s+(?:employee\s+)?(?:grievances?|disputes?|conflicts?|issues?)', ["Employee Relations"]),
    (r'(?:organized?|facilitated?|delivered?|conducted?)\s+(?:staff\s+|employee\s+)?training', ["Training", "L&D"]),
    (r'(?:recruited?|sourced?|hired?)\s+(?:\d+\s+)?(?:candidates?|employees?|staff)', ["Recruitment", "Talent Acquisition"]),
    (r'(?:managed?|oversaw?|supervised?)\s+(?:\d+\s+)?(?:employees?|staff|team\s+members?)', ["Team Management", "Leadership"]),
    (r'(?:developed?|implemented?)\s+(?:compensation|benefits|remuneration)\s+(?:packages?|structures?)', ["Compensation and Benefits", "Payroll"]),

    # ── Technical ──────────────────────────────────────────────────────────
    (r'(?:built?|developed?|created?|implemented?|designed?)\s+(?:a\s+)?(?:rest\s+)?(?:ful\s+)?api', ["REST APIs", "API Design"]),
    (r'(?:designed?|architected?|built?)\s+(?:the\s+)?(?:system|architecture|infrastructure|platform)', ["System Design", "Architecture"]),
    (r'(?:deployed?|launched?|migrated?)\s+(?:to\s+)?(?:aws|azure|gcp|cloud)', ["Cloud", "DevOps"]),
    (r'(?:containerized?|dockerized?|used?\s+docker)', ["Docker", "DevOps"]),
    (r'(?:set\s+up|configured?|implemented?|established?)\s+ci/?cd', ["CI/CD", "DevOps"]),
    (r'(?:optimized?|improved?|tuned?)\s+(?:database\s+)?(?:queries?|sql|performance)', ["Database Optimization", "SQL"]),
    (r'(?:trained?|built?|fine[- ]tuned?)\s+(?:a\s+)?(?:machine\s+learning\s+|ml\s+|ai\s+)?model', ["Machine Learning"]),
    (r'(?:built?|developed?|created?)\s+(?:a\s+)?(?:web\s+|mobile\s+)?(?:application|app|platform|portal|website)', ["Web Development", "Software Development"]),
    (r'(?:wrote?|developed?|maintained?)\s+(?:automated?\s+)?(?:unit\s+|integration\s+)?tests?', ["Unit Testing", "Testing"]),
    (r'(?:managed?|administered?)\s+(?:linux\s+|unix\s+)?(?:servers?|infrastructure)', ["Linux", "System Administration"]),

    # ── Marketing ──────────────────────────────────────────────────────────
    (r'(?:managed?|ran?|executed?|launched?)\s+(?:marketing\s+|digital\s+)?campaigns?', ["Campaign Management", "Marketing"]),
    (r'(?:increased?|grew?|improved?)\s+(?:website\s+|organic\s+)?traffic', ["SEO", "Digital Marketing"]),
    (r'(?:managed?|handled?|grew?)\s+(?:social\s+media|instagram|facebook|twitter|linkedin)', ["Social Media Marketing"]),
    (r'(?:created?|produced?|wrote?|developed?)\s+(?:marketing\s+|web\s+)?content', ["Content Marketing", "Copywriting"]),
    (r'(?:generated?|produced?|achieved?)\s+\d+\+?\s+leads?', ["Lead Generation"]),
    (r'(?:managed?|optimized?)\s+(?:google\s+)?(?:ads?|adwords|ppc)', ["Google Ads", "PPC"]),
    (r'(?:improved?|optimized?)\s+(?:search\s+engine|seo|organic\s+rankings?)', ["SEO"]),

    # ── Healthcare ─────────────────────────────────────────────────────────
    (r'(?:cared?\s+for|treated?|managed?\s+care\s+of)\s+(?:\d+\s+)?patients?', ["Patient Care", "Clinical Skills"]),
    (r'(?:administered?|gave?|dispensed?)\s+(?:medications?|drugs?|injections?|iv)', ["Medication Administration"]),
    (r'(?:conducted?|performed?|carried?\s+out)\s+clinical\s+(?:assessments?|evaluations?|examinations?)', ["Clinical Assessment"]),
    (r'(?:documented?|recorded?|maintained?)\s+(?:patient\s+)?(?:medical\s+)?(?:records?|history|notes?|charts?)', ["Medical Documentation", "EHR"]),
    (r'(?:diagnosed?|assessed?|evaluated?)\s+(?:patient\s+)?(?:conditions?|symptoms?|illnesses?)', ["Diagnosis", "Clinical Assessment"]),

    # ── Project Management ─────────────────────────────────────────────────
    (r'(?:managed?|led?|oversaw?)\s+(?:multiple\s+)?projects?', ["Project Management"]),
    (r'(?:delivered?|completed?)\s+(?:project|solution)\s+(?:on\s+time|within\s+budget|ahead\s+of\s+schedule)', ["Project Management", "Time Management"]),
    (r'(?:coordinated?|facilitated?)\s+(?:cross[- ]functional|multiple)\s+teams?', ["Coordination", "Collaboration"]),
    (r'(?:managed?|tracked?|monitored?)\s+(?:project\s+)?(?:timelines?|milestones?|deliverables?)', ["Project Management", "Planning"]),
    (r'(?:prepared?|written?|developed?)\s+(?:project\s+)?(?:proposals?|plans?|scope)', ["Project Management", "Planning"]),

    # ── Leadership & Management ────────────────────────────────────────────
    (r'managed?\s+(?:a\s+)?team\s+of\s+\d+', ["Leadership", "Team Management"]),
    (r'led?\s+(?:a\s+)?team\s+of\s+\d+', ["Leadership", "Team Management"]),
    (r'(?:supervised?|oversaw?)\s+\d+\s+(?:staff|employees?|people|reports?)', ["Leadership", "Supervision"]),
    (r'mentored?\s+(?:junior|graduate|new)\s+(?:staff|employees?|team\s+members?)', ["Mentoring", "Leadership"]),
    (r'(?:presented?|reported?)\s+to\s+(?:senior\s+)?(?:management|executives?|board|ceo|cfo)', ["Presentation Skills", "Stakeholder Management"]),

    # ── Sales ──────────────────────────────────────────────────────────────
    (r'(?:achieved?|exceeded?|surpassed?)\s+(?:sales\s+)?(?:targets?|quotas?|goals?)', ["Sales", "Target Achievement"]),
    (r'(?:closed?|won?|secured?)\s+(?:new\s+)?(?:deals?|contracts?|clients?|accounts?)', ["Sales", "Business Development"]),
    (r'(?:managed?|grew?|maintained?)\s+(?:a\s+)?(?:client|customer)\s+(?:portfolio|base|relationships?)', ["Account Management", "Client Relations"]),
    (r'(?:generated?|developed?)\s+(?:new\s+)?(?:business|revenue|leads?|opportunities?)', ["Business Development", "Sales"]),

    # ── General ────────────────────────────────────────────────────────────
    (r'(?:improved?|streamlined?|optimized?)\s+(?:business\s+)?(?:processes?|workflows?|procedures?)', ["Process Improvement"]),
    (r'(?:ensured?|maintained?|monitored?)\s+(?:regulatory\s+|legal\s+)?compliance', ["Compliance", "Regulatory"]),
    (r'(?:wrote?|drafted?|prepared?)\s+(?:business\s+|technical\s+)?(?:reports?|proposals?|documentation)', ["Report Writing", "Documentation"]),
    (r'(?:analyzed?|interpreted?)\s+(?:business\s+|market\s+)?data', ["Data Analysis"]),
    (r'(?:trained?|coached?|developed?)\s+(?:staff|employees?|team\s+members?)', ["Training", "Coaching"]),
]


def extract_contextual_skills(text: str) -> list[str]:
    """
    Extract skills implied by action phrases in resume text.
    Covers Finance, HR, IT, Marketing, Healthcare, Project Management.
    """
    found      = set()
    text_lower = text.lower()

    for pattern, skills in CONTEXTUAL_PATTERNS:
        if re.search(pattern, text_lower):
            found.update(skills)

    return list(found)