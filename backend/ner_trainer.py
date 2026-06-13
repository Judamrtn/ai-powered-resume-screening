"""
NER Trainer v2
Improved training with:
- Better skill patterns covering all industries
- HR, Finance, Healthcare, Legal, Marketing skills
- More certification patterns
- Better entity boundary handling
"""
import argparse
import json
import os
import random
import re
from pathlib import Path

import spacy
from spacy.tokens import DocBin
from spacy.training import Example

MODEL_OUTPUT = Path("models/resume_ner")
TRAIN_DATA   = Path("data/ner_training_data_v2.json")
DATASET_PATH = Path("data/Resume/Resume.csv")


def clean_entities(text: str, entities: list) -> list:
    cleaned = []
    for start, end, label in entities:
        if start < 0 or end > len(text) or start >= end:
            continue
        span_text = text[start:end]
        if span_text != span_text.strip():
            stripped  = span_text.strip()
            if not stripped:
                continue
            new_start = start + len(span_text) - len(span_text.lstrip())
            new_end   = new_start + len(stripped)
            if new_start < new_end <= len(text):
                cleaned.append((new_start, new_end, label))
        else:
            cleaned.append((start, end, label))

    cleaned.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    non_overlapping = []
    last_end = 0
    for start, end, label in cleaned:
        if start >= last_end:
            non_overlapping.append((start, end, label))
            last_end = end
    return non_overlapping


def build_skill_patterns():
    """Build comprehensive skill patterns covering all industries."""
    from esco_loader import get_all_skills_flat
    return get_all_skills_flat()


def build_training_data(csv_path: Path) -> list[dict]:
    import pandas as pd
    skills   = build_skill_patterns()
    df       = pd.read_csv(csv_path)
    examples = []

    print(f"Processing {len(df)} resumes from {len(df['Category'].unique())} categories...")
    print(f"Categories: {sorted(df['Category'].unique().tolist())}")

    for _, row in df.iterrows():
        text     = str(row.get("Resume_str", ""))
        category = str(row.get("Category", "")).lower()
        if not text or len(text) < 50:
            continue
        text     = text[:3000]
        entities = []

        # Skills — all industries
        for skill in skills:
            pattern = r'(?<![A-Za-z0-9])' + re.escape(skill) + r'(?![A-Za-z0-9])'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append((match.start(), match.end(), "SKILL"))

        # HR specific skills
        hr_skills = [
            "recruitment", "talent acquisition", "employee relations", "onboarding",
            "performance management", "hr policies", "payroll", "training",
            "compensation", "benefits", "workforce planning", "succession planning",
            "employee engagement", "organizational development", "hris", "workday",
            "diversity and inclusion", "labor relations", "job evaluation",
        ]
        if category in ["hr", "human resources"]:
            for skill in hr_skills:
                pattern = r'(?<![A-Za-z0-9])' + re.escape(skill) + r'(?![A-Za-z0-9])'
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append((match.start(), match.end(), "SKILL"))

        # Finance specific skills
        finance_skills = [
            "financial analysis", "budgeting", "forecasting", "accounting", "auditing",
            "tax preparation", "financial reporting", "accounts payable", "accounts receivable",
            "gaap", "ifrs", "variance analysis", "cost analysis", "financial modeling",
        ]
        if category in ["finance", "accounting", "banking"]:
            for skill in finance_skills:
                pattern = r'(?<![A-Za-z0-9])' + re.escape(skill) + r'(?![A-Za-z0-9])'
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append((match.start(), match.end(), "SKILL"))

        # Job titles — comprehensive
        job_pattern = (
            r'\b(?:Senior|Junior|Lead|Principal|Staff|Head\s+of|Chief)?\s*'
            r'(?:Software|Data|Machine\s+Learning|Frontend|Backend|Full[- ]Stack|'
            r'DevOps|Cloud|Security|Network|HR|Human\s+Resources|Finance|Marketing|'
            r'Sales|Operations|Clinical|Medical|Legal|Civil|Mechanical|Electrical|'
            r'Recruitment|Talent|Payroll|Accounting|Supply\s+Chain|Logistics)\s*'
            r'(?:Engineer|Developer|Analyst|Manager|Consultant|Specialist|Architect|'
            r'Officer|Director|Coordinator|Administrator|Nurse|Doctor|Lawyer|'
            r'Accountant|Recruiter|Generalist|Business\s+Partner)\b'
        )
        for match in re.finditer(job_pattern, text, re.IGNORECASE):
            entities.append((match.start(), match.end(), "JOB_TITLE"))

        # Education
        edu_pattern = (
            r'\b(?:Bachelor\'?s?|Master\'?s?|PhD|Doctorate|Associate|'
            r'Advanced\s+Diploma|Diploma|BSc|MSc|BA|MA|MBA|BEng|MEng|'
            r'B\.S\.|M\.S\.|B\.A\.|M\.A\.)\b'
        )
        for match in re.finditer(edu_pattern, text, re.IGNORECASE):
            entities.append((match.start(), match.end(), "EDUCATION"))

        # Certifications
        cert_pattern = (
            r'\b(?:PMP|CCNA|CCNP|CPA|CFA|ACCA|SHRM|PHR|SPHR|CISSP|CEH|CISM|'
            r'Scrum\s+Master|ITIL|Prince2|Six\s+Sigma|AWS\s+Certified|'
            r'Google\s+Certified|Microsoft\s+Certified|Cisco\s+Certified|'
            r'CompTIA|PMI|CISA|CISM|ISO|HACCP|LEED)\b'
        )
        for match in re.finditer(cert_pattern, text, re.IGNORECASE):
            entities.append((match.start(), match.end(), "CERTIFICATION"))

        clean = clean_entities(text, entities)
        if clean:
            examples.append({"text": text, "entities": clean})

    print(f"Built {len(examples)} training examples")
    return examples


def train_ner_model(training_data: list[dict], n_iter: int = 50):
    nlp = spacy.load("en_core_web_sm")
    ner = nlp.get_pipe("ner")

    for label in ["SKILL", "JOB_TITLE", "EDUCATION", "CERTIFICATION"]:
        ner.add_label(label)

    examples = []
    skipped  = 0
    for item in training_data:
        doc  = nlp.make_doc(item["text"])
        ents = []
        for start, end, label in item["entities"]:
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span is not None:
                ents.append(span)
        try:
            doc.ents = spacy.util.filter_spans(ents)
            example  = Example.from_dict(doc, {
                "entities": [(e.start_char, e.end_char, e.label_) for e in doc.ents]
            })
            examples.append(example)
        except Exception:
            skipped += 1

    print(f"Valid examples: {len(examples)} ({skipped} skipped)")
    print(f"Training for {n_iter} iterations...")

    optimizer   = nlp.resume_training()
    other_pipes = [p for p in nlp.pipe_names if p != "ner"]

    with nlp.disable_pipes(*other_pipes):
        for i in range(n_iter):
            random.shuffle(examples)
            losses  = {}
            batches = spacy.util.minibatch(examples, size=8)
            for batch in batches:
                try:
                    nlp.update(batch, sgd=optimizer, drop=0.3, losses=losses)
                except Exception:
                    continue
            if (i + 1) % 10 == 0:
                print(f"  Iteration {i+1}/{n_iter} — Loss: {losses.get('ner', 0):.4f}")

    os.makedirs(MODEL_OUTPUT, exist_ok=True)
    nlp.to_disk(MODEL_OUTPUT)
    print(f"\nModel saved to {MODEL_OUTPUT}")
    return nlp


def test_model():
    if not MODEL_OUTPUT.exists():
        print("No model found. Run --train first.")
        return

    nlp = spacy.load(MODEL_OUTPUT)

    # Test with HR resume
    hr_text = """
    Jane Smith - HR Manager
    Email: jane@example.com

    EXPERIENCE
    HR Manager at ABC Company (2020 - 2024)
    - Led recruitment process for 50+ positions
    - Conducted performance reviews for 200 employees
    - Developed HR policies and onboarding procedures
    - Managed employee relations and resolved grievances
    - Processed payroll for 300 staff

    EDUCATION
    Bachelor of Science in Human Resources - University of Nairobi (2015-2019)

    CERTIFICATIONS
    SHRM-CP | PHR

    SKILLS
    Recruitment, Employee Relations, Performance Management, HR Policies, Onboarding,
    Payroll, Training, HRIS, Workday, Talent Acquisition
    """

    doc = nlp(hr_text)
    print("\nHR Resume entities:")
    for ent in doc.ents:
        print(f"  [{ent.label_:15}] {ent.text}")

    # Test with IT resume
    it_text = """
    John Dev - Software Engineer
    EXPERIENCE
    Senior Software Engineer at Google (2021 - 2024)
    Built REST APIs using Python and FastAPI
    Deployed microservices on AWS using Docker and Kubernetes

    EDUCATION
    Bachelor of Science in Computer Science

    SKILLS
    Python, FastAPI, Docker, AWS, PostgreSQL, Machine Learning
    """
    doc2 = nlp(it_text)
    print("\nIT Resume entities:")
    for ent in doc2.ents:
        print(f"  [{ent.label_:15}] {ent.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--test",  action="store_true")
    parser.add_argument("--iter",  type=int, default=50)
    args = parser.parse_args()

    if args.train:
        if not DATASET_PATH.exists():
            print(f"Dataset not found at {DATASET_PATH}")
        else:
            data = build_training_data(DATASET_PATH)
            with open(TRAIN_DATA, "w") as f:
                json.dump(data, f)
            train_ner_model(data, n_iter=args.iter)

    if args.test:
        test_model()

    if not any([args.train, args.test]):
        parser.print_help()