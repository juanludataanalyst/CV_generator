import os
import json
import asyncio
import re
from dotenv import load_dotenv
from typing import Dict

from pydantic_ai import Agent
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel

load_dotenv()

def get_model():
    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    base_url = "https://openrouter.ai/api/v1"
    model_name = "openrouter/quasar-alpha"
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIModel(model_name, provider=provider)

agent = Agent(get_model())

async def extract_structured_data(text: str, is_job: bool = True) -> Dict:
    """
    Extracts skills, experience, and keywords from job description or resume text using LLM.
    """
    prompt = f"""
Extract the following information from this {'job description' if is_job else 'resume'}:
1. A list of required skills (e.g., "Python", "Machine Learning").
2. The minimum years of experience required (as a number, e.g., 3). If not specified, return 0.
3. The 10 most important keywords or phrases that should appear in a resume to match this job (e.g., "data analysis", "cloud computing").

Text:
\"\"\"
{text}
\"\"\"

Return the result as a JSON object with keys: "skills", "experience", "keywords".
Respond ONLY with the JSON object.
"""
    result = await agent.run(prompt)
    return json.loads(result.data)

def calculate_ats_score(job_data: Dict, resume_data: Dict, resume_text: str) -> Dict:
    """
    Calculates ATS compatibility score based on skills, experience, and keywords.
    """
    score = 0
    max_score = 100

    # Skills (40%)
    job_skills = set(s.lower() for s in job_data['skills'])
    resume_skills = set(s.lower() for s in resume_data['skills'])
    skill_matches = len(job_skills.intersection(resume_skills))
    skill_score = (skill_matches / max(len(job_skills), 1)) * 40 if job_skills else 40
    score += skill_score

    # Experience (30%)
    try:
        job_years = int(job_data['experience'])
    except:
        job_years = 0
    try:
        resume_years = int(resume_data['experience'])
    except:
        resume_years = 0

    if job_years == 0:
        exp_score = 30
    elif resume_years >= job_years:
        exp_score = 30
    else:
        exp_score = (resume_years / job_years) * 30
    score += exp_score

    # Keywords (30%)
    job_keywords = set(k.lower() for k in job_data['keywords'])
    resume_text_lower = resume_text.lower()
    keyword_matches = sum(1 for k in job_keywords if k in resume_text_lower)
    keyword_score = (keyword_matches / max(len(job_keywords), 1)) * 30 if job_keywords else 30
    score += keyword_score

    # Details
    missing_skills = list(job_skills - resume_skills)
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

def get_dynamic_prompt(gap: float, match_data: Dict, target_score: int) -> str:
    """
    Generates a dynamic prompt for the LLM based on the gap to the target score.
    """
    missing_skills = ", ".join(match_data["missing_skills"]) or "None"
    missing_keywords = ", ".join(match_data["missing_keywords"]) or "None"
    exp_gap = match_data["experience_gap"]

    if gap <= 10:
        instruction = (
            "The CV is close to the target ATS score. Emphasize existing skills, experience, and keywords "
            "that match the job description. Distribute them naturally across sections (e.g., summary, skills, work) "
            "to reinforce compatibility without major changes."
        )
    elif gap <= 30:
        instruction = (
            "The CV requires moderate adjustments to reach the target ATS score. Incorporate missing skills and keywords "
            "naturally into relevant sections (e.g., skills, work experience, summary). Adjust experience descriptions "
            "to align more closely with job requirements, closing minor gaps."
        )
    else:
        instruction = (
            "The CV needs significant optimization to reach the target ATS score. Rewrite key sections to include all "
            "missing skills and keywords from the job description where plausible. Enhance the experience section to "
            "minimize the gap, rephrasing or emphasizing relevant aspects to maximize ATS compatibility."
        )

    details = (
        f"\n\nOptimization details:\n"
        f"- Missing skills: {missing_skills}\n"
        f"- Missing keywords: {missing_keywords}\n"
        f"- Experience gap: {exp_gap} years"
    )
    return instruction + details

async def adapt_cv_to_job_async(cv_json: dict, job_description: str, target_score: int = 75) -> dict:
    """
    Adapts a CV JSON to a job description, aiming for a user-defined ATS target score (75-100%).
    """
    target_score = max(75, min(target_score, 100))

    cv_text = json.dumps(cv_json, indent=2)

    # Extract structured data
    job_data = await extract_structured_data(job_description, is_job=True)
    resume_data = await extract_structured_data(cv_text, is_job=False)

    # Calculate initial ATS score
    initial_match = calculate_ats_score(job_data, resume_data, cv_text)
    initial_score = initial_match['score']
    gap = max(target_score - initial_score, 0)

    print("\n=== Initial ATS Analysis ===")
    print(f"Initial ATS Score: {initial_score}%")
    print(f"Target ATS Score: {target_score}%")
    print(f"Gap to Target: {gap:.2f}%")
    print(f"Skills Matched: {initial_match['skill_matches']} / {initial_match['total_skills']}")
    print(f"Keywords Matched: {initial_match['keyword_matches']} / {initial_match['total_keywords']}")
    print(f"Experience: {initial_match['resume_years']} years (Job requires: {initial_match['job_years']})")
    print(f"Missing Skills: {initial_match['missing_skills']}")
    print(f"Missing Keywords: {initial_match['missing_keywords']}")
    print(f"Experience Gap: {initial_match['experience_gap']} years")

    # Generate dynamic prompt
    instruction = get_dynamic_prompt(gap, initial_match, target_score)

    prompt = f"""
You are an expert CV writer and ATS optimizer.

Your goal is to optimize the CV to achieve approximately **{target_score}% compatibility** with the company's ATS system for the provided job description.

Follow these instructions to adapt the CV:
{instruction}

**Guidelines:**
- Maintain the JSON Resume format.
- Do not invent false information, but you may add plausible skills or keywords from the job description if they align with the candidate's background or are learnable, especially for higher target scores.
- Seamlessly integrate changes into descriptive sections (e.g., summary, work experience, skills).
- Ensure a professional and natural tone.

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
    json_str = result.data
    # Ocultar salida cruda del LLM
    try:
        updated_cv = json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError("Failed to parse LLM output as JSON")

    # Recalculate ATS score
    updated_cv_text = json.dumps(updated_cv, indent=2)
    updated_resume_data = await extract_structured_data(updated_cv_text, is_job=False)
    final_match = calculate_ats_score(job_data, updated_resume_data, updated_cv_text)
    updated_cv["ats_match_score"] = final_match["score"]

    print("\n=== Final ATS Analysis ===")
    print(f"Final ATS Score: {final_match['score']}%")
    print(f"Skills Matched: {final_match['skill_matches']} / {final_match['total_skills']}")
    print(f"Keywords Matched: {final_match['keyword_matches']} / {final_match['total_keywords']}")
    print(f"Experience: {final_match['resume_years']} years (Job requires: {final_match['job_years']})")

    return updated_cv

def adapt_cv_to_job(cv_json: dict, job_description: str, target_score: int = 75) -> dict:
    """
    Synchronous wrapper for async CV adaptation.
    """
    return asyncio.run(adapt_cv_to_job_async(cv_json, job_description, target_score))
