"""
Notification Templates

Plain-text templates with {variable} substitution, matching spec 4.11's
"Configurable notification templates with dynamic variable substitution."

These are intentionally simple Python format-strings rather than a full
templating engine (Jinja2 etc.) - there's no current need for loops or
conditionals inside a template, and keeping this dependency-free means
one less thing that can break. If template complexity grows later,
swapping these dict entries for Jinja2 Template objects is a contained
change that won't touch any calling code.
"""
from __future__ import annotations

TEMPLATES: dict[str, dict[str, str]] = {

    "application_received": {
        "subject": "Application Received - {job_title}",
        "body": (
            "Dear {candidate_name},\n\n"
            "Thank you for applying to the {job_title} position"
            "{department_clause}. We have successfully received your "
            "application and resume.\n\n"
            "Our team will review your application and reach out if "
            "your qualifications match our requirements.\n\n"
            "Best regards,\n"
            "The Recruitment Team"
        ),
    },

    "status_changed": {
        "subject": "Update on your application - {job_title}",
        "body": (
            "Dear {candidate_name},\n\n"
            "We wanted to update you on the status of your application "
            "for {job_title}.\n\n"
            "Your application status has changed to: {new_status}\n\n"
            "{status_specific_message}\n\n"
            "Best regards,\n"
            "The Recruitment Team"
        ),
    },

    "interview_scheduled": {
        "subject": "Interview Scheduled - {job_title}",
        "body": (
            "Dear {candidate_name},\n\n"
            "We are pleased to invite you to an interview for the "
            "{job_title} position.\n\n"
            "Format:    {interview_format}\n"
            "Date/Time: {scheduled_at}\n"
            "Duration:  {duration_minutes} minutes\n"
            "{location_clause}"
            "{meeting_link_clause}\n"
            "Please confirm your attendance at your earliest "
            "convenience. If you have any scheduling conflicts, let us "
            "know as soon as possible.\n\n"
            "Best regards,\n"
            "The Recruitment Team"
        ),
    },

    "interview_reminder": {
        "subject": "Reminder: Interview Tomorrow - {job_title}",
        "body": (
            "Dear {candidate_name},\n\n"
            "This is a friendly reminder of your upcoming interview for "
            "{job_title}.\n\n"
            "Format:    {interview_format}\n"
            "Date/Time: {scheduled_at}\n"
            "{location_clause}"
            "{meeting_link_clause}\n"
            "We look forward to speaking with you.\n\n"
            "Best regards,\n"
            "The Recruitment Team"
        ),
    },

    "recruiter_alert_high_scorer": {
        "subject": "New high-scoring applicant - {job_title}",
        "body": (
            "Hi {recruiter_name},\n\n"
            "A new applicant for {job_title} scored {score}% on initial "
            "screening, which is above your alert threshold.\n\n"
            "Candidate: {candidate_name}\n"
            "Recommendation: {recommendation}\n\n"
            "Review their full profile in the dashboard.\n\n"
            "- AI Resume Screening System"
        ),
    },
}


# Human-readable follow-up lines per pipeline status, slotted into the
# status_changed template's {status_specific_message} variable.
STATUS_MESSAGES = {
    "screening":   "Your application is currently under review by our recruitment team.",
    "shortlisted": "Congratulations - you have been shortlisted for this role. We will be in touch shortly regarding next steps.",
    "interview":   "You have been moved forward to the interview stage. You should receive a separate interview invitation shortly.",
    "offer":       "We are pleased to inform you that you are being considered for an offer. A member of our team will reach out directly.",
    "hired":       "Congratulations! We are delighted to welcome you to the team. Further onboarding details will follow separately.",
    "rejected":    "After careful consideration, we have decided not to move forward with your application at this time. We appreciate the time you invested and encourage you to apply for future openings that match your skills.",
}


def render_template(template_key: str, variables: dict) -> tuple[str, str]:
    """
    Render a template by key, substituting variables. Returns
    (subject, body). Raises KeyError if the template doesn't exist, or
    ValueError if a required variable is missing - both are deliberate
    fail-loud behaviors rather than silently sending a half-broken
    email with literal "{candidate_name}" still in the text.
    """
    if template_key not in TEMPLATES:
        raise KeyError(f"Unknown notification template: {template_key}")

    template = TEMPLATES[template_key]
    try:
        subject = template["subject"].format(**variables)
        body    = template["body"].format(**variables)
    except KeyError as e:
        raise ValueError(
            f"Template '{template_key}' requires variable {e}, which was "
            f"not provided. Provided variables: {sorted(variables.keys())}"
        ) from e

    return subject, body