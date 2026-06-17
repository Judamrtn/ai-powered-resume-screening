"""
Comprehensive Contextual Skills Extractor
Covers ALL experience levels across ALL industries:
- Intern/Entry: shadowed, assisted, helped, participated, contributed
- Junior: performed, processed, supported, maintained, created
- Mid: coordinated, facilitated, executed, implemented, handled, managed
- Senior: led, developed, designed, built, conducted, established
- Executive: oversaw, directed, spearheaded, championed, transformed
"""
from __future__ import annotations
import re

# ── Action verb groups by level ───────────────────────────────────────────────
INTERN    = r'(?:shadowed?|observed?|participated?\s+in|contributed?\s+to|assisted?\s+(?:with|in)|helped?\s+(?:with|in)|involved?\s+in|supported?|learned?|gained?\s+experience\s+in|exposed?\s+to)'
JUNIOR    = r'(?:performed?|processed?|maintained?|created?|prepared?|completed?|handled?|executed?|carried?\s+out|conducted?|organized?|updated?|entered?|recorded?|filed?|drafted?)'
MID       = r'(?:coordinated?|facilitated?|implemented?|managed?|monitored?|tracked?|reviewed?|analyzed?|analysed?|evaluated?|assessed?|resolved?|improved?|developed?|delivered?|ensured?)'
SENIOR    = r'(?:led?|designed?|built?|established?|launched?|deployed?|architected?|directed?|oversaw?|supervised?|mentored?|trained?|restructured?|transformed?|optimized?|streamlined?)'
EXEC      = r'(?:spearheaded?|championed?|drove?|pioneered?|orchestrated?|formulated?|defined?|envisioned?|scaled?|grew?|expanded?|repositioned?)'
ANY_LEVEL = f'(?:{INTERN}|{JUNIOR}|{MID}|{SENIOR}|{EXEC})'

CONTEXTUAL_PATTERNS = [

    # ════════════════════════════════════════════════════════
    # FINANCE & ACCOUNTING
    # ════════════════════════════════════════════════════════

    # Financial reporting
    (rf'{ANY_LEVEL}\s+(?:monthly|annual|quarterly|weekly|daily)?\s*(?:basic\s+)?financial\s+(?:statements?|reports?|accounts?|documents?|records?)',
     ["Financial Reporting", "Accounting"]),
    (rf'{ANY_LEVEL}\s+(?:management|board|executive)\s+(?:reports?|presentations?)',
     ["Financial Reporting", "Presentation Skills"]),
    (r'(?:expense|invoice)\s+(?:tracking|processing|management|reconciliation)',
     ["Expense Management", "Accounts Payable"]),

    # Bookkeeping & accounting
    (rf'{ANY_LEVEL}\s+(?:daily\s+)?bookkeeping\s+(?:activities?|tasks?|duties?)?',
     ["Bookkeeping", "Accounting"]),
    (rf'{ANY_LEVEL}\s+(?:general\s+)?ledger(?:\s+entries?|\s+accounts?)?',
     ["Bookkeeping", "Accounting"]),
    (rf'{ANY_LEVEL}\s+(?:accounts?\s+)?(?:payable|receivable)(?:\s+processes?)?',
     ["Accounts Payable", "Accounting"]),
    (rf'{ANY_LEVEL}\s+bank\s+(?:statements?|accounts?|reconciliations?)',
     ["Bank Reconciliation", "Accounting"]),
    (rf'{ANY_LEVEL}\s+financial\s+(?:records?|documents?|files?|invoices?|data)',
     ["Financial Documentation", "Accounting"]),
    (rf'{ANY_LEVEL}\s+(?:data\s+entry|simple\s+financial\s+calculations?|basic\s+accounting)',
     ["Data Entry", "Accounting"]),

    # Budgeting
    (rf'{ANY_LEVEL}\s+(?:annual|operational|departmental|project)?\s*budgets?(?:\s+of\s+[\d,\$€£]+)?',
     ["Budgeting", "Budget Management"]),
    (rf'{ANY_LEVEL}\s+(?:budget|financial)\s+(?:forecasts?|projections?|models?)',
     ["Forecasting", "Financial Modeling"]),
    (rf'(?:reduced?|cut|decreased?)\s+costs?\s+by\s+\d+',
     ["Cost Reduction", "Financial Analysis"]),
    (rf'(?:increased?|grew?|improved?)\s+(?:revenue|profit|sales)\s+by\s+\d+',
     ["Revenue Growth", "Financial Analysis"]),

    # Auditing & compliance
    (rf'{ANY_LEVEL}\s+(?:internal|external|statutory)?\s*audits?',
     ["Auditing", "Compliance"]),
    (rf'{ANY_LEVEL}\s+(?:tax\s+)?(?:returns?|filings?|declarations?|submissions?)',
     ["Tax Preparation", "Compliance"]),
    (rf'(?:ensured?|maintained?|monitored?)\s+(?:regulatory|legal|statutory|financial)?\s*compliance',
     ["Compliance", "Regulatory"]),
    (rf'{ANY_LEVEL}\s+(?:vat|gst|paye|tax)\s+(?:returns?|filings?|calculations?)',
     ["Tax Preparation", "Accounting"]),

    # Payroll
    (rf'{ANY_LEVEL}\s+payroll(?:\s+for\s+\d+\s+(?:staff|employees?))?',
     ["Payroll", "Accounting"]),
    (rf'{ANY_LEVEL}\s+(?:salary|compensation|benefits)\s+(?:processing|calculations?|administration)',
     ["Payroll", "Compensation and Benefits"]),

    # ════════════════════════════════════════════════════════
    # HUMAN RESOURCES
    # ════════════════════════════════════════════════════════

    # Recruitment
    (rf'{ANY_LEVEL}\s+(?:candidates?|applicants?|resumes?|cvs?)',
     ["Recruitment", "Talent Acquisition"]),
    (rf'{ANY_LEVEL}\s+(?:job\s+)?(?:postings?|advertisements?|vacancies?|openings?)',
     ["Recruitment"]),
    (rf'{ANY_LEVEL}\s+(?:job\s+)?interviews?(?:\s+with\s+candidates?)?',
     ["Interviewing", "Recruitment"]),
    (rf'{ANY_LEVEL}\s+(?:new\s+)?(?:employees?|staff|hires?|joiners?)\s+(?:onboarding|orientation|induction)',
     ["Onboarding"]),
    (rf'onboard(?:ed|ing)?\s+(?:\d+\s+)?(?:new\s+)?(?:employees?|staff|hires?)',
     ["Onboarding"]),

    # Performance management
    (rf'{ANY_LEVEL}\s+(?:performance\s+)?(?:reviews?|appraisals?|evaluations?|assessments?)',
     ["Performance Management"]),
    (rf'{ANY_LEVEL}\s+(?:kpis?|okrs?|goals?|targets?)\s+(?:for\s+(?:staff|team|employees?))?',
     ["Performance Management", "Goal Setting"]),

    # HR policies & relations
    (rf'{ANY_LEVEL}\s+(?:hr\s+)?(?:policies|procedures|guidelines|handbooks?|frameworks?)',
     ["HR Policies"]),
    (rf'{ANY_LEVEL}\s+(?:employee|staff|workplace)\s+(?:grievances?|disputes?|conflicts?|complaints?|issues?)',
     ["Employee Relations", "Conflict Resolution"]),
    (rf'{ANY_LEVEL}\s+(?:staff|employee|workforce)\s+(?:training|development|learning)',
     ["Training", "L&D"]),
    (rf'{ANY_LEVEL}\s+(?:compensation|benefits|remuneration)\s+(?:packages?|structures?|schemes?)',
     ["Compensation and Benefits", "Payroll"]),
    (rf'{ANY_LEVEL}\s+(?:workforce|headcount|staffing)\s+(?:planning|forecasting|management)',
     ["Workforce Planning", "HR"]),

    # ════════════════════════════════════════════════════════
    # INFORMATION TECHNOLOGY
    # ════════════════════════════════════════════════════════

    # Development
    (rf'{ANY_LEVEL}\s+(?:rest\s+)?(?:ful\s+)?(?:web\s+)?api(?:s|\s+endpoints?)?',
     ["REST APIs", "API Design"]),
    (rf'{ANY_LEVEL}\s+(?:web|mobile|desktop|cloud)?\s*(?:application|app|platform|portal|website|system)',
     ["Software Development", "Web Development"]),
    (rf'{ANY_LEVEL}\s+(?:microservices?|serverless|distributed)\s+(?:architecture|system)',
     ["Microservices", "System Design"]),
    (rf'{ANY_LEVEL}\s+(?:the\s+)?(?:system|software|application|database)\s+architecture',
     ["System Design", "Architecture"]),

    # DevOps & Cloud
    (rf'{ANY_LEVEL}\s+(?:to\s+)?(?:aws|azure|gcp|cloud)\s+(?:infrastructure|environment|platform)?',
     ["Cloud", "DevOps"]),
    (rf'(?:containerized?|dockerized?|used?\s+docker\s+to)',
     ["Docker", "DevOps"]),
    (rf'{ANY_LEVEL}\s+(?:kubernetes|k8s)\s+(?:clusters?|deployments?|pods?)?',
     ["Kubernetes", "DevOps"]),
    (rf'{ANY_LEVEL}\s+ci/?cd\s+(?:pipelines?|workflows?)?',
     ["CI/CD", "DevOps"]),

    # Data & ML
    (rf'{ANY_LEVEL}\s+(?:machine\s+learning|ml|ai|deep\s+learning)\s+(?:models?|algorithms?|pipelines?)',
     ["Machine Learning", "AI"]),
    (rf'{ANY_LEVEL}\s+(?:data\s+)?(?:pipelines?|etl\s+processes?|workflows?)',
     ["Data Engineering", "ETL"]),
    (rf'{ANY_LEVEL}\s+(?:sql|database)\s+(?:queries?|schemas?|optimizations?)',
     ["SQL", "Database Optimization"]),

    # Testing & Security
    (rf'{ANY_LEVEL}\s+(?:unit|integration|regression|end-to-end)?\s*tests?(?:\s+using\s+\w+)?',
     ["Testing", "Quality Assurance"]),
    (rf'{ANY_LEVEL}\s+(?:security\s+)?(?:vulnerabilities?|threats?|risks?|audits?)',
     ["Cybersecurity", "Security"]),

    # ════════════════════════════════════════════════════════
    # MARKETING & SALES
    # ════════════════════════════════════════════════════════

    (rf'{ANY_LEVEL}\s+(?:marketing|digital|social\s+media|email)?\s*campaigns?',
     ["Campaign Management", "Marketing"]),
    (rf'{ANY_LEVEL}\s+(?:website|organic|paid)?\s*(?:traffic|rankings?|visibility)',
     ["SEO", "Digital Marketing"]),
    (rf'{ANY_LEVEL}\s+(?:social\s+media|instagram|facebook|twitter|linkedin|tiktok)',
     ["Social Media Marketing"]),
    (rf'{ANY_LEVEL}\s+(?:marketing|web|blog|social\s+media)?\s*content',
     ["Content Marketing", "Copywriting"]),
    (rf'(?:generated?|produced?|achieved?)\s+\d+\+?\s+leads?',
     ["Lead Generation"]),
    (rf'{ANY_LEVEL}\s+(?:google\s+)?(?:ads?|adwords|ppc|paid\s+(?:search|media))',
     ["Google Ads", "PPC"]),
    (rf'(?:exceeded?|achieved?|surpassed?)\s+(?:sales\s+)?(?:targets?|quotas?|goals?)',
     ["Sales", "Target Achievement"]),
    (rf'{ANY_LEVEL}\s+(?:client|customer|account)\s+(?:relationships?|portfolio|base)',
     ["Account Management", "Client Relations"]),
    (rf'{ANY_LEVEL}\s+(?:new\s+)?(?:business|revenue|deals?|contracts?|opportunities?)',
     ["Business Development", "Sales"]),

    # ════════════════════════════════════════════════════════
    # HEALTHCARE
    # ════════════════════════════════════════════════════════

    (rf'{ANY_LEVEL}\s+(?:care\s+(?:for|of)\s+)?(?:\d+\s+)?patients?',
     ["Patient Care", "Clinical Skills"]),
    (rf'{ANY_LEVEL}\s+(?:medications?|drugs?|prescriptions?|injections?|iv)',
     ["Medication Administration", "Clinical Skills"]),
    (rf'{ANY_LEVEL}\s+clinical\s+(?:assessments?|examinations?|evaluations?|trials?)',
     ["Clinical Assessment", "Clinical Research"]),
    (rf'{ANY_LEVEL}\s+(?:patient\s+)?(?:medical\s+)?(?:records?|history|notes?|charts?|documentation)',
     ["Medical Documentation", "EHR"]),
    (rf'{ANY_LEVEL}\s+(?:patient\s+)?(?:conditions?|symptoms?|diagnoses?|illnesses?)',
     ["Diagnosis", "Clinical Assessment"]),
    (rf'{ANY_LEVEL}\s+(?:ward|clinic|theatre|icu|emergency)\s+(?:duties?|rounds?|procedures?)?',
     ["Patient Care", "Clinical Skills"]),

    # ════════════════════════════════════════════════════════
    # PROJECT MANAGEMENT
    # ════════════════════════════════════════════════════════

    (rf'{ANY_LEVEL}\s+(?:multiple\s+)?(?:concurrent\s+)?projects?(?:\s+simultaneously)?',
     ["Project Management"]),
    (rf'{ANY_LEVEL}\s+(?:project\s+)?(?:timelines?|milestones?|deliverables?|schedules?)',
     ["Project Management", "Planning"]),
    (rf'{ANY_LEVEL}\s+(?:cross[- ]functional|interdepartmental|multiple)\s+teams?',
     ["Coordination", "Collaboration", "Stakeholder Management"]),
    (rf'(?:delivered?|completed?)\s+(?:project|solution)\s+(?:on\s+time|within\s+budget|ahead\s+of\s+schedule)',
     ["Project Management", "Time Management"]),
    (rf'{ANY_LEVEL}\s+(?:project\s+)?(?:risks?|issues?|dependencies?|blockers?)',
     ["Risk Management", "Project Management"]),
    (rf'{ANY_LEVEL}\s+(?:agile|scrum|kanban|waterfall)\s+(?:methodology|framework|processes?)',
     ["Agile", "Scrum", "Project Management"]),

    # ════════════════════════════════════════════════════════
    # LEADERSHIP & MANAGEMENT
    # ════════════════════════════════════════════════════════

    (rf'(?:managed?|led?|supervised?)\s+(?:a\s+)?team\s+of\s+\d+',
     ["Leadership", "Team Management"]),
    (rf'(?:managed?|supervised?|oversaw?)\s+\d+\s+(?:staff|employees?|people|direct\s+reports?)',
     ["Leadership", "Supervision"]),
    (rf'{ANY_LEVEL}\s+(?:junior|graduate|new|entry[- ]level)\s+(?:staff|employees?|team\s+members?)',
     ["Mentoring", "Leadership"]),
    (rf'(?:presented?|reported?|briefed?)\s+(?:to\s+)?(?:senior\s+)?(?:management|executives?|board|ceo|cfo|directors?)',
     ["Presentation Skills", "Stakeholder Management"]),
    (rf'{ANY_LEVEL}\s+(?:team\s+)?(?:performance|productivity|morale|culture)',
     ["Leadership", "Team Management"]),

    # ════════════════════════════════════════════════════════
    # ENGINEERING & CONSTRUCTION
    # ════════════════════════════════════════════════════════

    (rf'{ANY_LEVEL}\s+(?:mechanical|civil|structural|electrical|chemical)?\s*(?:engineering\s+)?(?:designs?|drawings?|specifications?)',
     ["Engineering", "Technical Drawing"]),
    (rf'{ANY_LEVEL}\s+(?:construction|building|infrastructure)\s+(?:projects?|sites?|works?)',
     ["Construction Management", "Project Management"]),
    (rf'{ANY_LEVEL}\s+(?:quality\s+)?(?:inspections?|checks?|testing|assurance)',
     ["Quality Control", "Quality Assurance"]),
    (rf'{ANY_LEVEL}\s+(?:safety|hse|health\s+and\s+safety)\s+(?:procedures?|protocols?|standards?)',
     ["Safety Management", "HSE"]),
    (rf'{ANY_LEVEL}\s+(?:autocad|solidworks|catia|revit|bim)\s+(?:models?|drawings?|designs?)?',
     ["AutoCAD", "3D Modeling"]),

    # ════════════════════════════════════════════════════════
    # EDUCATION & TRAINING
    # ════════════════════════════════════════════════════════

    (rf'{ANY_LEVEL}\s+(?:lesson\s+plans?|curriculum|course\s+materials?|syllabi?)',
     ["Curriculum Development", "Lesson Planning"]),
    (rf'{ANY_LEVEL}\s+(?:classes?|lectures?|sessions?|workshops?|seminars?)',
     ["Teaching", "Training", "Facilitation"]),
    (rf'{ANY_LEVEL}\s+(?:student|learner|trainee)\s+(?:performance|progress|assessments?|evaluations?)',
     ["Student Assessment", "Teaching"]),
    (rf'{ANY_LEVEL}\s+(?:e-?learning|online\s+courses?|lms|moodle|blackboard)',
     ["E-learning", "Educational Technology"]),

    # ════════════════════════════════════════════════════════
    # LOGISTICS & SUPPLY CHAIN
    # ════════════════════════════════════════════════════════

    (rf'{ANY_LEVEL}\s+(?:inventory|stock)\s+(?:levels?|management|control|counts?)',
     ["Inventory Management", "Supply Chain"]),
    (rf'{ANY_LEVEL}\s+(?:supplier|vendor)\s+(?:relationships?|negotiations?|management)',
     ["Vendor Management", "Procurement"]),
    (rf'{ANY_LEVEL}\s+(?:shipments?|deliveries?|freight|logistics)\s+(?:operations?|management|coordination)',
     ["Logistics Management", "Supply Chain"]),
    (rf'{ANY_LEVEL}\s+(?:purchase\s+orders?|pos?|procurement)\s+(?:processes?|activities?)',
     ["Procurement", "Supply Chain"]),

    # ════════════════════════════════════════════════════════
    # GENERAL / CROSS-INDUSTRY
    # ════════════════════════════════════════════════════════

    (rf'{ANY_LEVEL}\s+(?:business\s+|operational\s+)?(?:processes?|workflows?|procedures?)',
     ["Process Improvement", "Operations"]),
    (rf'(?:ensured?|maintained?|monitored?)\s+(?:regulatory|legal|industry)\s+(?:compliance|standards?)',
     ["Compliance", "Regulatory"]),
    (rf'{ANY_LEVEL}\s+(?:business|technical|management|executive)?\s*(?:reports?|dashboards?|presentations?)',
     ["Reporting", "Communication"]),
    (rf'{ANY_LEVEL}\s+(?:business\s+|market\s+|financial\s+)?data\s+(?:analysis|analytics|insights?)',
     ["Data Analysis"]),
    (rf'{ANY_LEVEL}\s+(?:staff|employees?|team\s+members?|colleagues?)',
     ["Training", "Coaching"]),
    (rf'(?:improved?|increased?|enhanced?|optimized?)\s+(?:efficiency|productivity|performance|output)\s+by\s+\d+',
     ["Process Improvement", "Performance Management"]),
    (rf'(?:saved?|reduced?)\s+(?:\$|€|£|rwf|ugx)?[\d,]+\s+(?:in\s+)?(?:costs?|expenses?|time)',
     ["Cost Reduction", "Financial Analysis"]),
]


def extract_contextual_skills(text: str) -> list[str]:
    """
    Extract skills implied by action phrases across ALL industries
    and ALL experience levels (intern to executive).
    """
    found      = set()
    text_lower = text.lower()

    for pattern, skills in CONTEXTUAL_PATTERNS:
        try:
            if re.search(pattern, text_lower):
                found.update(skills)
        except re.error:
            continue

    return list(found)