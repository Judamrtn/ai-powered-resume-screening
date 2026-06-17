from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

app = FastAPI(title="AI Resume Screening System", version="1.0.0")

from routers.auth import router as auth_router
from routers.jobs import router as jobs_router
from routers.candidate import router as candidates_router
from routers.interview import router as interview_router

app.include_router(interview_router)
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(candidates_router)


# ---------------- HOME ----------------
@app.get("/")
def home():
    return {"message": "AI Resume Screening System", "version": "1.0.0"}


# ---------------- DEBUG: Extract raw text from PDF ----------------
@app.post("/debug/text")
async def debug_text(file: UploadFile = File(...)):
    """Debug endpoint — shows raw extracted text from a PDF."""
    content  = await file.read()
    filename = f"uploads/{uuid.uuid4()}.pdf"
    os.makedirs("uploads", exist_ok=True)
    with open(filename, "wb") as f:
        f.write(content)
    try:
        from resume_parser import parse_pdf
        text = parse_pdf(filename)
        return {"length": len(text), "text": text[:5000]}
    finally:
        if os.path.exists(filename):
            os.remove(filename)


# ---------------- DEBUG: Education detection ----------------
@app.post("/debug/education")
async def debug_education(file: UploadFile = File(...)):
    """Debug endpoint — shows education detection results."""
    content  = await file.read()
    filename = f"uploads/{uuid.uuid4()}.pdf"
    os.makedirs("uploads", exist_ok=True)
    with open(filename, "wb") as f:
        f.write(content)
    try:
        from resume_parser import parse_pdf
        from composite_scorer import extract_education_level, score_education
        text        = parse_pdf(filename)
        name, rank  = extract_education_level(text)
        score       = score_education(text, "Bachelor's")
        return {
            "education_found": name,
            "rank_found":      rank,
            "score":           score,
            "text_snippet":    text[:500],
        }
    finally:
        if os.path.exists(filename):
            os.remove(filename)


# ---------------- DEBUG: Scoring breakdown ----------------
@app.post("/debug/score")
async def debug_score(file: UploadFile = File(...), job_id: str = None):
    """Debug endpoint — shows full scoring breakdown."""
    content  = await file.read()
    filename = f"uploads/{uuid.uuid4()}.pdf"
    os.makedirs("uploads", exist_ok=True)
    with open(filename, "wb") as f:
        f.write(content)
    try:
        from resume_parser import parse_pdf
        from extractor import extract_email, extract_phone, extract_name
        from services.skills import extract_skills
        from contextual_extractor import extract_contextual_skills
        from experience_extractor import extract_years_of_experience
        from composite_scorer import extract_education_level, score_education, detect_domain
        from taxonomy import normalize_skills

        text   = parse_pdf(filename)
        skills = extract_skills(text)
        tech   = normalize_skills(skills.get("technical_skills", []))
        ctx    = extract_contextual_skills(text)
        edu_name, edu_rank = extract_education_level(text)
        exp_years = extract_years_of_experience(text)

        return {
            "name":              extract_name(text),
            "email":             extract_email(text),
            "detected_skills":   tech,
            "contextual_skills": ctx,
            "education_found":   edu_name,
            "education_rank":    edu_rank,
            "education_score":   score_education(text, "Bachelor's"),
            "experience_years":  exp_years,
            "domain":            detect_domain(text),
        }
    finally:
        if os.path.exists(filename):
            os.remove(filename)