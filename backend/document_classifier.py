"""
Document Type Classifier
Detects whether an uploaded PDF is:
- resume/cv
- certificate/credential
- cover_letter
- transcript
- reference_letter
- other

Uses rule-based scoring first, then falls back to NLP if needed.
Rejects non-resume documents before scoring.
"""
from __future__ import annotations
import re
from dataclasses import dataclass


# ── Signal patterns per document type ────────────────────────────────────────

RESUME_SIGNALS = [
    # Strong signals
    (r'\b(?:work\s+experience|professional\s+experience|employment\s+history)\b', 3),
    (r'\b(?:curriculum\s+vitae|cv|resume)\b',                                     3),
    (r'\b(?:education|academic\s+background|qualifications)\b',                   2),
    (r'\b(?:skills|technical\s+skills|core\s+competencies)\b',                    2),
    (r'\b(?:objective|summary|profile|about\s+me)\b',                             2),
    (r'\b(?:references?|referees?)\b',                                             1),
    (r'\b(?:projects?|achievements?|accomplishments?)\b',                          1),
    (r'\b(?:certifications?|licenses?|awards?)\b',                                 1),
    # Date ranges typical of work history
    (r'\b\d{4}\s*[-–]\s*(?:\d{4}|present|current)\b',                            2),
    # Job titles
    (r'\b(?:engineer|developer|manager|analyst|designer|consultant|officer|'
     r'director|coordinator|specialist|administrator|nurse|doctor|teacher|'
     r'accountant|lawyer)\b',                                                      1),
]

CERTIFICATE_SIGNALS = [
    (r'\b(?:this\s+certifies?\s+that|has\s+(?:successfully\s+)?completed)\b',     4),
    (r'\b(?:certificate\s+of\s+(?:completion|achievement|participation))\b',       4),
    (r'\b(?:awarded\s+to|presented\s+to|this\s+is\s+to\s+certify)\b',            4),
    (r'\b(?:hours?\s+(?:of\s+)?(?:training|study|learning|viewed))\b',            3),
    (r'\b(?:date\s+of\s+(?:completion|issue|award))\b',                           3),
    (r'\b(?:authorized\s+by|issued\s+by|signed\s+by)\b',                          2),
    (r'\b(?:co-?founder|instructor|examiner|proctor)\b',                           2),
    (r'\b(?:edutainer|facilitator|certifying\s+authority)\b',                      2),
]

COVER_LETTER_SIGNALS = [
    (r'\bdear\s+(?:hiring\s+manager|sir|madam|mr\.|ms\.|dr\.)\b',                4),
    (r'\bi\s+am\s+writing\s+to\s+(?:apply|express\s+my\s+interest)\b',           4),
    (r'\b(?:i\s+look\s+forward\s+to\s+hearing\s+from\s+you)\b',                  3),
    (r'\b(?:sincerely|yours\s+faithfully|best\s+regards)\b',                      3),
    (r'\bplease\s+find\s+(?:my|the)\s+(?:attached|enclosed)\b',                   3),
]

TRANSCRIPT_SIGNALS = [
    (r'\b(?:official\s+transcript|academic\s+transcript|grade\s+report)\b',       4),
    (r'\b(?:gpa|grade\s+point\s+average|cumulative\s+gpa)\b',                     3),
    (r'\b(?:credit\s+hours?|semester\s+hours?|units\s+earned)\b',                 3),
    (r'\b(?:pass|fail|incomplete|withdrawn|audited)\b',                            2),
    (r'\b(?:registrar|academic\s+records)\b',                                      3),
]

REFERENCE_SIGNALS = [
    (r'\b(?:to\s+whom\s+it\s+may\s+concern)\b',                                   4),
    (r'\b(?:i\s+(?:am\s+pleased\s+to|wholeheartedly)\s+recommend)\b',             4),
    (r'\b(?:reference\s+letter|letter\s+of\s+recommendation)\b',                   4),
    (r'\b(?:during\s+(?:his|her|their)\s+time\s+(?:at|with|under))\b',            3),
]


@dataclass
class DocumentClassification:
    doc_type:    str      # resume | certificate | cover_letter | transcript | reference_letter | other
    confidence:  float    # 0-100
    is_resume:   bool
    reason:      str
    scores:      dict


def classify_document(text: str) -> DocumentClassification:
    """
    Classify a document by type using signal-based scoring.
    Returns classification with confidence score.
    """
    text_lower = text.lower()
    word_count = len(text.split())

    # Score each document type
    type_scores = {
        "resume":           0,
        "certificate":      0,
        "cover_letter":     0,
        "transcript":       0,
        "reference_letter": 0,
    }

    for pattern, weight in RESUME_SIGNALS:
        if re.search(pattern, text_lower):
            type_scores["resume"] += weight

    for pattern, weight in CERTIFICATE_SIGNALS:
        if re.search(pattern, text_lower):
            type_scores["certificate"] += weight

    for pattern, weight in COVER_LETTER_SIGNALS:
        if re.search(pattern, text_lower):
            type_scores["cover_letter"] += weight

    for pattern, weight in TRANSCRIPT_SIGNALS:
        if re.search(pattern, text_lower):
            type_scores["transcript"] += weight

    for pattern, weight in REFERENCE_SIGNALS:
        if re.search(pattern, text_lower):
            type_scores["reference_letter"] += weight

    # Very short documents are likely not resumes
    if word_count < 100:
        type_scores["resume"] = max(0, type_scores["resume"] - 3)

    # Determine winner
    best_type  = max(type_scores, key=type_scores.get)
    best_score = type_scores[best_type]

    # If no strong signals found
    if best_score == 0:
        best_type = "other"

    # Normalize confidence (max possible resume score ~20)
    max_possible = {"resume": 20, "certificate": 16, "cover_letter": 14,
                    "transcript": 15, "reference_letter": 14, "other": 5}
    confidence = min(
        round((best_score / max_possible.get(best_type, 10)) * 100, 1),
        100
    )

    # Determine if it's a resume
    is_resume = (
        best_type == "resume" and
        type_scores["resume"] >= 4 and
        type_scores["resume"] > type_scores["certificate"] and
        type_scores["resume"] > type_scores["cover_letter"]
    )

    # Build reason message
    if is_resume:
        reason = f"Document appears to be a resume (confidence: {confidence}%)"
    elif best_type == "certificate":
        reason = "Document appears to be a certificate or credential, not a resume"
    elif best_type == "cover_letter":
        reason = "Document appears to be a cover letter, not a resume"
    elif best_type == "transcript":
        reason = "Document appears to be an academic transcript, not a resume"
    elif best_type == "reference_letter":
        reason = "Document appears to be a reference letter, not a resume"
    else:
        reason = "Could not determine document type — may not be a resume"

    return DocumentClassification(
        doc_type   = best_type,
        confidence = confidence,
        is_resume  = is_resume,
        reason     = reason,
        scores     = type_scores,
    )


def validate_resume(text: str) -> tuple[bool, str]:
    """
    Validate that a document is a resume.
    Returns (is_valid, error_message).
    """
    classification = classify_document(text)

    if classification.is_resume:
        return True, ""

    # Allow low-confidence resumes through with warning
    if (classification.doc_type == "resume" and
            classification.scores["resume"] >= 2):
        return True, ""

    return False, (
        f"{classification.reason}. "
        f"Please upload a CV or resume document. "
        f"Detected type: {classification.doc_type.replace('_', ' ').title()}"
    )