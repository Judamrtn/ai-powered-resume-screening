"""
Experience Extractor
Extracts total years of experience from resume text using two strategies:
1. Explicit phrases: "5 years of experience", "3+ years"
2. Date ranges: "2020 - 2023", "Jan 2019 - Mar 2022", "2018 - Present"
"""
from __future__ import annotations
import re
from datetime import datetime

CURRENT_YEAR = datetime.now().year
CURRENT_MONTH = datetime.now().month

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}


# ── Date parsing helpers ──────────────────────────────────────────────────────

def parse_year_month(text: str) -> tuple[int, int] | None:
    """
    Parse a date string into (year, month).
    Handles: '2020', 'Jan 2020', 'January 2020', '2020-01', '01/2020'
    """
    text = text.strip().lower()

    # Present / current / now
    if text in ("present", "current", "now", "today"):
        return (CURRENT_YEAR, CURRENT_MONTH)

    # Month Year: "jan 2020", "january 2020"
    m = re.match(r'([a-z]+)\s+(\d{4})', text)
    if m:
        month = MONTH_MAP.get(m.group(1)[:3])
        year  = int(m.group(2))
        if month and 1990 <= year <= CURRENT_YEAR + 1:
            return (year, month)

    # Year Month: "2020 jan", "2020-01"
    m = re.match(r'(\d{4})[-\s](\d{1,2}|[a-z]+)', text)
    if m:
        year = int(m.group(1))
        try:
            month = int(m.group(2))
        except ValueError:
            month = MONTH_MAP.get(m.group(2)[:3], 1)
        if 1990 <= year <= CURRENT_YEAR + 1:
            return (year, month)

    # Year only: "2020"
    m = re.match(r'^(\d{4})$', text)
    if m:
        year = int(m.group(1))
        if 1990 <= year <= CURRENT_YEAR + 1:
            return (year, 1)

    return None


def months_between(start: tuple[int, int], end: tuple[int, int]) -> float:
    """Calculate months between two (year, month) tuples."""
    return (end[0] - start[0]) * 12 + (end[1] - start[1])


# ── Strategy 1: Explicit phrase extraction ────────────────────────────────────

def extract_years_from_phrases(text: str) -> float:
    patterns = [
        r'(\d+(?:\.\d+)?)\+?\s*years?\s+of\s+(?:professional\s+)?experience',
        r'(\d+(?:\.\d+)?)\+?\s*years?\s+experience',
        r'experience\s+of\s+(\d+(?:\.\d+)?)\+?\s*years?',
        r'(\d+(?:\.\d+)?)\+?\s*yrs?\s+(?:of\s+)?experience',
        r'over\s+(\d+(?:\.\d+)?)\s*years?\s+(?:of\s+)?experience',
        r'more\s+than\s+(\d+(?:\.\d+)?)\s*years?\s+(?:of\s+)?experience',
    ]
    years_found = []
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        years_found.extend([float(m) for m in matches])
    return max(years_found) if years_found else 0.0


# ── Strategy 2: Date range extraction ────────────────────────────────────────

EDUCATION_CONTEXT_PATTERNS = [
    r'(?:university|college|institute|school|academy|polytechnic)',
    r'(?:bachelor|master|phd|diploma|degree|bsc|msc|ba|ma|mba)',
    r'(?:graduated|graduation|enrolled|studied|gpa|cgpa|cumulative)',
]


def is_education_date_range(text: str, start: int, end: int) -> bool:
    """
    Check if a date range appears near education keywords.
    If so, it's likely an education date, not work experience.
    """
    # Get surrounding context (200 chars before and after)
    context = text[max(0, start - 200):end + 200].lower()
    for pattern in EDUCATION_CONTEXT_PATTERNS:
        if re.search(pattern, context):
            return True
    return False


def extract_years_from_date_ranges(text: str) -> float:
    """
    Find all date ranges in text and sum unique non-overlapping durations.
    Skips date ranges that appear near education keywords.
    Examples matched:
      - "2020 - 2023"
      - "Jan 2019 - Mar 2022"
      - "2018 - Present"
      - "March 2020 to Current"
    """
    sep      = r'\s*(?:–|—|-|to)\s*'
    date_tok = r'(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+)?\d{4}|present|current|now'
    pattern  = rf'({date_tok}){sep}({date_tok})'

    parsed_ranges = []
    text_lower    = text.lower()

    for match in re.finditer(pattern, text_lower):
        start_str = match.group(1).strip()
        end_str   = match.group(2).strip()
        start     = parse_year_month(start_str)
        end       = parse_year_month(end_str)

        if not start or not end or end < start:
            continue

        duration = months_between(start, end)
        if not (1 <= duration <= 600):
            continue

        # Skip if this date range is near education keywords
        if is_education_date_range(text_lower, match.start(), match.end()):
            continue

        parsed_ranges.append((start, end, duration))

    if not parsed_ranges:
        return 0.0

    # Sort and merge overlapping ranges
    parsed_ranges.sort(key=lambda x: x[0])
    merged = [parsed_ranges[0]]
    for start, end, _ in parsed_ranges[1:]:
        last_start, last_end, _ = merged[-1]
        if start <= last_end:
            new_end      = max(last_end, end)
            new_duration = months_between(last_start, new_end)
            merged[-1]   = (last_start, new_end, new_duration)
        else:
            merged.append((start, end, months_between(start, end)))

    total_months = sum(d for _, _, d in merged)
    return round(total_months / 12, 1)


# ── Combined extractor ────────────────────────────────────────────────────────

def extract_years_of_experience(text: str) -> float:
    """
    Extract total years of experience using both strategies.
    Returns the higher of the two estimates.
    """
    phrase_years    = extract_years_from_phrases(text)
    date_range_years = extract_years_from_date_ranges(text)

    # Take the maximum — one strategy may work better for a given resume
    return max(phrase_years, date_range_years)


def score_experience(resume_text: str, required_years: int | None) -> float:
    """
    Score experience 0-100 based on detected vs required years.
    Returns 50.0 if no requirement specified (neutral).
    """
    if not required_years:
        return 50.0

    found_years = extract_years_of_experience(resume_text)

    if found_years == 0:
        return 20.0  # couldn't detect — partial credit

    if found_years >= required_years:
        bonus = min((found_years - required_years) * 5, 20)
        return min(100.0, 80.0 + bonus)
    else:
        return round((found_years / required_years) * 75, 2)