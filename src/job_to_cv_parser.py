import os
import json
import asyncio
import re
from dotenv import load_dotenv
from typing import Dict
from dateutil import parser
from datetime import datetime

from pydantic_ai import Agent

load_dotenv()

async def extract_structured_data(text: str, agent: Agent, is_job: bool = True) -> Dict:
    """
    Extracts skills, experience, and keywords from a job description or CV using an LLM.
    """
    print("Extracting structured data from " + ("job description" if is_job else "CV") + "...")
    if is_job:
        prompt = f"""
Extract the following information from this job description:
1. A list of ALL required skills (e.g., "Python", "Machine Learning").
2. The minimum years of experience required (as a number, e.g., 3). If not specified, return 0.
3. The 10 most important keywords or phrases that should appear in a resume to match this job (e.g., "data analysis", "cloud computing").

Text:
\"\"\"
{text}
\"\"\"

Return the result as a JSON object with keys: "skills", "experience", "keywords".
Respond ONLY with the JSON object.
"""
    else:
        prompt = f"""
Extract the following information from this CV:
1. A list of ALL mentioned skills.
2. The 10 most important keywords or phrases representing the candidate's experience.

Text:
\"\"\"
{text}
\"\"\"

Return the result as a JSON object with keys: "skills", "keywords".
Respond ONLY with the JSON object.
"""
    result = await agent.run(prompt)
    print("LLM response (job_to_cv_parser):")
    print(result.data)
    if not result.data.strip():
        raise ValueError("LLM returned an empty response in extract_structured_data.")
    try:
        parsed = json.loads(result.data)
    except json.JSONDecodeError:
        print("Error: LLM response is not valid JSON:")
        print(result.data)
        raise
    print("Structured data extracted successfully.")
    return parsed

def calculate_total_experience(cv_json: dict) -> int:
    """
    Calculates total years of experience from the 'work' section of the CV JSON.
    """
    work_entries = cv_json.get("work", [])
    if not work_entries:
        return 0

    earliest_start = None
    latest_end = None

    for entry in work_entries:
        start_str = entry.get("startDate")
        end_str = entry.get("endDate", "")  # If endDate is empty, it's a current job

        if start_str:
            try:
                start_date = parser.parse(start_str)
                if earliest_start is None or start_date < earliest_start:
                    earliest_start = start_date
            except:
                continue

        if end_str:
            try:
                end_date = parser.parse(end_str)
                if latest_end is None or end_date > latest_end:
                    latest_end = end_date
            except:
                continue
        else:
            # Current job, use today's date
            latest_end = datetime.now()

    if earliest_start and latest_end:
        total_years = (latest_end - earliest_start).days / 365.25
        return int(total_years)
    return 0

def calculate_ats_score(job_data: Dict, resume_data: Dict, resume_text: str, cv_json: dict) -> Dict:
    """
    Calculates the ATS compatibility score based on skills, experience, and keywords.
    """
    score = 0
    max_score = 100

    # Habilidades (40%)
    job_skills = set(s.lower() for s in job_data['skills'])

    # Extraer tokens individuales de las skills del CV
    resume_skill_tokens = set()
    resume_skills_lower = []
    for skill in resume_data['skills']:
        skill_l = skill.lower()
        resume_skills_lower.append(skill_l)
        tokens = skill_l.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
        resume_skill_tokens.update(tokens)

    skill_matches = 0
    for js in job_skills:
        if ' ' in js:
            # Skill de varias palabras: buscar como substring en alguna skill del CV
            if any(js in skill for skill in resume_skills_lower):
                skill_matches += 1
        else:
            # Skill de una palabra: buscar en tokens
            if js in resume_skill_tokens:
                skill_matches += 1

    skill_score = (skill_matches / max(len(job_skills), 1)) * 40 if job_skills else 40
    score += skill_score

    # Experiencia (30%)
    try:
        job_years = int(job_data['experience'])
    except:
        job_years = 0
    resume_years = calculate_total_experience(cv_json)
    if job_years == 0:
        exp_score = 30
    elif resume_years >= job_years:
        exp_score = 30
    else:
        exp_score = (resume_years / job_years) * 30
    score += exp_score

    # Palabras clave (30%)
    job_keywords = set(k.lower() for k in job_data['keywords'])
    resume_text_lower = resume_text.lower()
    keyword_matches = sum(1 for k in job_keywords if k in resume_text_lower)
    keyword_score = (keyword_matches / max(len(job_keywords), 1)) * 30 if job_keywords else 30
    score += keyword_score

    # Detalles
    missing_skills = []
    for js in job_skills:
        if ' ' in js:
            if not any(js in skill for skill in resume_skills_lower):
                missing_skills.append(js)
        else:
            if js not in resume_skill_tokens:
                missing_skills.append(js)

    missing_keywords = [k for k in job_keywords if k not in resume_text_lower]
    exp_gap = max(job_years - resume_years, 0)

    return {
        'score': min(round(score, 2), max_score),
        'missing_skills': missing_skills,
        'missing_keywords': missing_keywords,
        'experience_gap': exp_gap,
        'skill_matches': skill_matches,
        'total_skills': len(job_skills),
        'keyword_matches': keyword_matches,
        'total_keywords': len(job_keywords),
        'resume_years': resume_years,
        'job_years': job_years
    }

async def adapt_cv_to_job_async(cv_json: dict, job_description: str, agent: Agent) -> dict:
    """
    Adapts a CV JSON to a job description, optimizing it to the maximum ethically achievable level.
    Shows real-time logs to the user.
    """
    print("Starting CV optimization process...")
    cv_text = json.dumps(cv_json, indent=2)

    # Extract structured data from job description
    job_data = await extract_structured_data(job_description, agent, is_job=True)
    print("Analyzing initial CV compatibility with the job description...")
    resume_data = await extract_structured_data(cv_text, agent, is_job=False)

    # Calculate initial ATS score
    initial_match = calculate_ats_score(job_data, resume_data, cv_text, cv_json)
    initial_score = initial_match['score']

    print("\n=== Initial ATS Analysis ===")
    print(f"Initial ATS Score: {initial_score}%")
    print(f"Matching Skills: {initial_match['skill_matches']} / {initial_match['total_skills']}")
    print(f"Matching Keywords: {initial_match['keyword_matches']} / {initial_match['total_keywords']}")
    print(f"Experience: {initial_match['resume_years']} years (Job requires: {initial_match['job_years']})")
    print(f"Missing Skills: {initial_match['missing_skills']}")
    print(f"Missing Keywords: {initial_match['missing_keywords']}")
    print(f"Experience Gap: {initial_match['experience_gap']} years")

    # If initial score is below 75%, proceed with optimization
    if initial_score < 75:
        print("\nOptimizing the CV to reach the maximum ethically achievable ATS score...")
        prompt = f"""
You are an expert in CV writing and ATS optimization.

Your goal is to optimize the CV to reach the highest ethically achievable compatibility percentage with the company's ATS system for the provided job description.

Instructions:
- Analyze the skills, experience, and keywords of the CV and compare them with the job description.
- Highlight and emphasize the candidate's existing strengths that match the requirements.
- Incorporate missing skills and keywords from the job description only if they are plausible given the candidate's profile or reasonably learnable, distributing them naturally across sections (e.g., summary, work experience, skills).
- Do not invent false information.
- Preserve all work experience entries with their original start and end dates.
- **Preserve all social profiles (e.g., LinkedIn) in the `basics.profiles` section.**
- Maintain the JSON Resume format and a professional, natural tone.

Initial compatibility details:
- Missing skills: {', '.join(initial_match['missing_skills']) or 'None'}
- Missing keywords: {', '.join(initial_match['missing_keywords']) or 'None'}
- Experience gap: {initial_match['experience_gap']} years

Job Description:
\"\"\"
{job_description}
\"\"\"

CV JSON:
\"\"\"
{cv_text}
\"\"\"

Return the updated CV as a JSON object.
Respond ONLY with the updated CV as a valid JSON object.
"""
        result = await agent.run(prompt)
        updated_cv = json.loads(result.data)
    else:
        print("\nInitial ATS score is already sufficiently high (>=75%). No optimization needed.")
        updated_cv = cv_json

    # Recalculate final ATS score
    print("Calculating final ATS score of the optimized CV...")
    updated_cv_text = json.dumps(updated_cv, indent=2)
    updated_resume_data = await extract_structured_data(updated_cv_text, agent, is_job=False)
    final_match = calculate_ats_score(job_data, updated_resume_data, updated_cv_text, updated_cv)
    updated_cv["ats_match_score"] = final_match["score"]

    print("\n=== Final ATS Analysis ===")
    print(f"Final ATS Score (Maximum Ethically Achievable): {final_match['score']}%")
    print(f"Matching Skills: {final_match['skill_matches']} / {final_match['total_skills']}")
    print(f"Matching Keywords: {final_match['keyword_matches']} / {final_match['total_keywords']}")
    print(f"Experience: {final_match['resume_years']} years (Job requires: {final_match['job_years']})")
    print("CV optimization process completed.")

    return updated_cv

def adapt_cv_to_job(cv_json: dict, job_description: str, agent: Agent) -> dict:
    """
    Synchronous wrapper for async CV adaptation.
    """
    return asyncio.run(adapt_cv_to_job_async(cv_json, job_description, agent))

# Ejemplo de uso
if __name__ == "__main__":
    # CV JSON de ejemplo
    cv_json = {
        "basics": {
            "name": "Juan Luis Pérez",
            "label": "DATA ANALYST",
            "summary": "Data-driven problem solver with expertise in SQL, Python, and Power BI."
        },
        "work": [
            {"company": "Scopely", "position": "Data Analyst", "startDate": "2018-09", "endDate": "2022-12"},
            {"company": "R10", "position": "Data Strategy Owner", "startDate": "2025-01", "endDate": ""}
        ],
        "skills": [
            {"name": "SQL"}, {"name": "Python"}, {"name": "Power BI"}
        ]
    }
    job_description = """
    Senior Data Analyst role requiring SQL, Python, Power BI, Tableau, and 3+ years of experience.
    Focus on game analytics, A/B testing, and player retention.
    """
    updated_cv = adapt_cv_to_job(cv_json, job_description)
    with open("adapted_resume.json", "w", encoding="utf-8") as f:
        json.dump(updated_cv, f, indent=2)
    print("CV adaptado guardado en adapted_resume.json")
