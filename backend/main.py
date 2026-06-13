from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from dotenv import load_dotenv
import os
import uuid
import hashlib

load_dotenv()

from resume_parser import parse_pdf
from extractor import extract_email, extract_phone, extract_name
from services.skills import extract_skills
from services.embedding import get_embedding
from services.ranking import cosine_similarity

app = FastAPI(title="AI Resume Screening System", version="1.0.0")

from routers.auth import router as auth_router
from routers.jobs import router as jobs_router
from routers.candidate import router as candidates_router
from routers.gap_analysis import router as gap_router


app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(candidates_router)
app.include_router(gap_router)

# ---------------- HOME ----------------
@app.get("/")
def home():
    return {"message": "AI Resume Screening System", "version": "1.0.0"}