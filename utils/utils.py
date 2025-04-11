from pdfminer.high_level import extract_text
import openai
import streamlit as st
import json
from typing import Dict
import os
from src.models import JsonResume

import time

import requests
from bs4 import BeautifulSoup, Comment

from dateutil import parser
from datetime import datetime

def extract_cv_text(pdf_path: str) -> str:
    """
    Extracts text from a PDF CV file using pdfminer.six.
    """
    try:
        text = extract_text(pdf_path)
        with open("prueba", 'w', encoding='utf-8') as archivo:
            archivo.writelines(text)
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"]
)

def run_llm(prompt, temperature=0.1):
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-lite-001",
            messages=[
                {"role": "system", "content": "You are an expert assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
        )
        if not response.choices or len(response.choices) == 0:
            print("LLM returned empty choices")
            return None
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in LLM call: {e}")
        return None


def parse_to_json_resume_sync(text: str) -> Dict:
    """
    Parses CV text into JSON Resume format using an LLM via OpenRouter with pydantic-ai.
    """
    prompt = f"""
        You are an expert in CV parsing.

        Take the following extracted CV text, which may have mixed sections (e.g., Profile and Experience blended due to layout issues), and structure it into the JSON Resume standard format.

        Separate clearly the "Profile" (summary) from "Professional Experience" (work history with dates and descriptions) and other sections like Education, Skills, Languages, and Projects.

        Preserve the original content without adding or modifying information beyond structuring.

        Here is the pydantic model for reference:

            class Location(BaseModel):
                address: Optional[str] = None
                postalCode: Optional[str] = None
                city: Optional[str] = None
                countryCode: Optional[str] = None
                region: Optional[str] = None

            class Profile(BaseModel):
                network: Optional[str] = None
                username: Optional[str] = None
                url: Optional[HttpUrl] = None

            class Basics(BaseModel):
                name: str
                label: Optional[str] = None
                email: Optional[EmailStr] = None
                phone: Optional[str] = None
                url: Optional[HttpUrl] = None
                summary: Optional[str] = None
                location: Optional[Location] = None
                profiles: Optional[List[Profile]] = []

            class Work(BaseModel):
                company: str
                position: str
                website: Optional[HttpUrl] = None
                startDate: Optional[str] = None
                endDate: Optional[str] = None
                summary: Optional[str] = None
                highlights: Optional[List[str]] = []

            class Education(BaseModel):
                institution: str
                area: Optional[str] = None
                studyType: Optional[str] = None
                startDate: Optional[str] = None
                endDate: Optional[str] = None
                score: Optional[str] = None
                courses: Optional[List[str]] = []

            class Skill(BaseModel):
                name: str
                level: Optional[str] = None
                keywords: Optional[List[str]] = []

            class Language(BaseModel):
                language: str
                fluency: Optional[str] = None

            class Project(BaseModel):
                name: str
                description: Optional[str] = None
                highlights: Optional[List[str]] = []
                keywords: Optional[List[str]] = []
                startDate: Optional[str] = None
                endDate: Optional[str] = None
                url: Optional[HttpUrl] = None
                roles: Optional[List[str]] = []
                entity: Optional[str] = None
                type: Optional[str] = None

            class JsonResume(BaseModel):
                basics: Basics
                work: List[Work] = []
                education: List[Education] = []
                skills: List[Skill] = []
                languages: List[Language] = []
                projects: List[Project] = []

        Here is the JSON Resume schema for reference:
        - basics: {{\"name\": ..., \"label\": ..., \"email\": ..., \"phone\": ..., \"url\": ..., \"summary\": ..., \"location\": {{\"address\": ..., \"postalCode\": ..., \"city\": ..., \"countryCode\": ..., \"region\": ...}}, \"profiles\": [{{\"network\": ..., \"username\": ..., \"url\": ...}}]}}
        - work: [{{\"company\": ..., \"position\": ..., \"website\": ..., \"startDate\": ..., \"endDate\": ..., \"summary\": ..., \"highlights\": [...]}}]
        - education: [{{\"institution\": ..., \"area\": ..., \"studyType\": ..., \"startDate\": ..., \"endDate\": ..., \"score\": ..., \"courses\": [...]}}]
        - skills: [{{\"name\": ..., \"level\": ..., \"keywords\": [...]}}]
        - languages: [{{\"language\": ..., \"fluency\": ...}}]
        - projects: [{{\"name\": ..., \"description\": ..., \"highlights\": [...], \"keywords\": [...], \"startDate\": ..., \"endDate\": ..., \"url\": ..., \"roles\": [...], \"entity\": ..., \"type\": ...}}]

        Important rules:
        1. For URL fields (url, website), always use full URLs starting with \"http://\" or \"https://\". If a URL is relative or missing, set the field to null.
        2. For the location field inside basics, if any location sub-field is missing or empty, set the entire location field to null. Do not use empty strings for any location sub-fields.
        3. If any field is missing or cannot be extracted from the provided text, set that field to null. Do not use empty strings.
        4. Return the result as a valid JSON object.

        CV Text:
        \"\"\"
        {text}
        \"\"\"

        Return the result as a JSON object.
        """
            

    attempt = 0

    max_retries = 3
    for attempt in range(max_retries):
        result = run_llm(prompt)
        print("LLM response (cv_parser):")
        print(result)
        open("file_outputs/job_standar_llm_output.txt", 'w', encoding='utf-8').write(result)

        if not result or not result.strip():
            print(f"LLM returned empty response. Retry {attempt+1}/{max_retries}...")
            time.sleep(60)
            continue

        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            json_str = result.split("```")[1].split("```")[0].strip()
        else:
            json_str = result.strip()

        try:
            json_cv = json.loads(json_str)
            print(f"Parsed JSON before preprocessing: {json_cv['basics']['location']}")
            break  # Success
        except json.JSONDecodeError:
            print("Failed to parse LLM output as JSON:")
            print(json_str)
            if attempt < max_retries - 1:
                print(f"Retrying LLM call ({attempt+1}/{max_retries})...")
                time.sleep(3)
                continue
            else:
                raise ValueError("Failed to parse LLM output as JSON after retries")

      

    def preprocess_json(data):
     if isinstance(data, dict):
        new_data = {}
        if "basics" in data:
            new_data["basics"] = {}
        for k, v in data.items():
            if isinstance(v, str):
                if k in ("url", "website") and (v.strip() == "" or v.strip() is None):
                    new_data[k] = None
                elif k in ("url", "website") and not v.startswith("http") and v is not None:
                    new_data[k] = "https://" + v.lstrip("/")
                else:
                    new_data[k] = v
            elif isinstance(v, (dict, list)):
                new_data[k] = preprocess_json(v)
            elif k == "location" and "basics" in data:
                print(f"Location antes: {v}") #debug
                if v == "" or (isinstance(v, dict) and not any(v.values())):
                    new_data["basics"]["location"] = None
                    print("Location despues: None") #debug
                else:
                    new_data["basics"]["location"] = v
                    print(f"Location despues: {v}") #debug
            else:
                new_data[k] = v
        return new_data
     elif isinstance(data, list):
        return [preprocess_json(item) for item in data]
     else:
        return data

    json_cv = preprocess_json(json_cv)

    def replace_null_strings(data):
        list_fields = {"profiles", "highlights", "courses", "keywords", "roles"}
        if isinstance(data, dict):
            for k, v in data.items():
                if k in ("url", "website"):
                    if v is None or v == "":
                        data[k] = None
                elif k in list_fields:
                    if v is None or v == "":
                        data[k] = []
                    elif isinstance(v, (dict, list)):
                        replace_null_strings(v)
                elif k == "location":  # No modificar location si es None
                    continue
                elif v is None:
                    data[k] = ""
                elif isinstance(v, (dict, list)):
                    replace_null_strings(v)
        elif isinstance(data, list):
            for item in data:
                replace_null_strings(item)
        return data

    json_cv = replace_null_strings(json_cv)

    validated_cv = JsonResume(**json_cv)
    return validated_cv.model_dump(mode="json")

def scrape_job_description(url: str) -> str:
    """
    Extracts the job description from a job posting URL using HTML filtering and an LLM agent.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form", "iframe"]):
            tag.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        candidates = []
        keywords = ["description", "job", "responsibilities", "details", "requirements", "posting", "vacancy", "position", "role", "summary", "body", "content"]

        for tag in soup.find_all(["main", "article", "section", "div"]):
            text = tag.get_text(separator=" ", strip=True)
            if not text or len(text.split()) < 30:
                continue
            score = 0
            attrs = (tag.get("class", []) or []) + [tag.get("id", "")]
            attrs_text = " ".join(attrs).lower()
            if any(k in attrs_text for k in keywords):
                score += 2
            if any(k in text.lower() for k in keywords):
                score += 1
            candidates.append((score, len(text), tag))

        candidates.sort(reverse=True)

        if candidates:
            content = candidates[0][2]
        else:
            content = soup.body

        plain_text = content.get_text(separator="\n", strip=True)

        print(f"[DEBUG] Filtered content length: {len(plain_text)}")
        print(f"[DEBUG] Filtered content starts with: {plain_text[:100]}")

        try:
            with open("job_description.txt", "w", encoding="utf-8") as f:
                f.write(plain_text)
            print("Saved job_description.txt successfully.")
        except Exception as e:
            print(f"Error saving job_description.txt: {e}")

        #print("Filtered content preview:")
        #print(plain_text[:1000])

        prompt = f"""
        Extract only the main job description from the following text. Ignore menus, footers, ads, or irrelevant content.

        If this is not a job posting, respond with exactly: "ERROR: Not a job posting".

        Return only the job description without any additional comments:

        \"\"\"
        {plain_text}
        \"\"\"
        """

        max_retries = 3
        for attempt in range(max_retries):
          result = run_llm(prompt)
          print("LLM response (job_scraper):")
          print(result)
          open("file_outputs/job_description_llm_output.txt", 'w', encoding='utf-8').write(result)

        if not result or not result.strip():
            print(f"LLM returned empty response. Retry {attempt+1}/{max_retries}...")
            time.sleep(60)
        
        return result.strip()

    except requests.RequestException as e:
        return f"Error extracting content: {str(e)}"

def extract_description_data(text: str, is_job: bool = True) -> Dict:
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
        
        max_retries = 3
        for attempt in range(max_retries):
          result = run_llm(prompt)
          print("LLM response (cv_parser):")
          print(result)
          open("file_outputs/job_description_llm_output.txt", 'w', encoding='utf-8').write(result)

        if not result or not result.strip():
            print(f"LLM returned empty response. Retry {attempt+1}/{max_retries}...")
            time.sleep(60)
            

        

        print("LLM response (job_to_cv_parser):")
        print(result)

        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            json_str = result.split("```")[1].split("```")[0].strip()
        else:
            json_str = result.strip()

        if not json_str:
            raise ValueError("LLM returned an empty response in extract_structured_data.")
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            print("Error: LLM response is not valid JSON:")
            print(json_str)
            raise
        print("Structured data extracted successfully.")
        return parsed

def calculate_ats_score(parsed_cv: dict, job_data: dict) -> dict:
    """
    Calculates ATS score comparing parsed CV and job description data.
    """
    score = 0
    max_score = 100

    # Skills (40%)
    job_skills = set(s.lower() for s in job_data.get('skills', []))

    # CV skills
    resume_skill_tokens = set()
    resume_skills_lower = []
    for skill in parsed_cv.get('skills', []):
        if isinstance(skill, dict):
            skill_name = skill.get('name', '').lower()
        elif isinstance(skill, str):
            skill_name = skill.lower()
        else:
            continue
        resume_skills_lower.append(skill_name)
        tokens = skill_name.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
        resume_skill_tokens.update(tokens)

    skill_matches = 0
    for js in job_skills:
        if ' ' in js:
            if any(js in skill for skill in resume_skills_lower):
                skill_matches += 1
        else:
            if js in resume_skill_tokens:
                skill_matches += 1

    skill_score = (skill_matches / max(len(job_skills), 1)) * 40 if job_skills else 40
    score += skill_score

    # Experience (30%)
    try:
        job_years = int(job_data.get('experience', 0))
    except:
        job_years = 0
    resume_years = 0  # Puedes usar tu función calculate_total_experience aquí
    if job_years == 0:
        exp_score = 30
    elif resume_years >= job_years:
        exp_score = 30
    else:
        exp_score = (resume_years / job_years) * 30
    score += exp_score

    # Keywords (30%)
    job_keywords = set(k.lower() for k in job_data.get('keywords', []))
    resume_text_lower = json.dumps(parsed_cv).lower()
    keyword_matches = sum(1 for k in job_keywords if k in resume_text_lower)
    keyword_score = (keyword_matches / max(len(job_keywords), 1)) * 30 if job_keywords else 30
    score += keyword_score

    # Details
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



def adapt_cv_to_job(cv_json: dict, job_description: str) -> dict:
    """
    Adapts a CV JSON to a job description, optimizing it to the maximum ethically achievable level.
    Shows real-time logs to the user.
    """
    print("Starting CV optimization process...")
    cv_text = json.dumps(cv_json, indent=2)

  

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

        # Skills (40%)
        job_skills = set(s.lower() for s in job_data['skills'])

        # Extract individual tokens from CV skills
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
                # Multi-word skill: look for as substring in CV skills
                if any(js in skill for skill in resume_skills_lower):
                    skill_matches += 1
            else:
                # Single-word skill: look in tokens
                if js in resume_skill_tokens:
                    skill_matches += 1

        skill_score = (skill_matches / max(len(job_skills), 1)) * 40 if job_skills else 40
        score += skill_score

        # Experience (30%)
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

        # Keywords (30%)
        job_keywords = set(k.lower() for k in job_data['keywords'])
        resume_text_lower = resume_text.lower()
        keyword_matches = sum(1 for k in job_keywords if k in resume_text_lower)
        keyword_score = (keyword_matches / max(len(job_keywords), 1)) * 30 if job_keywords else 30
        score += keyword_score

        # Details
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

    # Extract structured data from job description
    job_data = extract_structured_data(job_description, is_job=True)
    print("Analyzing initial CV compatibility with the job description...")
    resume_data = extract_structured_data(cv_text, is_job=False)

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
        result = run_llm(prompt)
        updated_cv = json.loads(result)
    else:
        print("\nInitial ATS score is already sufficiently high (>=75%). No optimization needed.")
        updated_cv = cv_json

    # Recalculate final ATS score
    print("Calculating final ATS score of the optimized CV...")
    updated_cv_text = json.dumps(updated_cv, indent=2)
    updated_resume_data = extract_structured_data(updated_cv_text, is_job=False)
    final_match = calculate_ats_score(job_data, updated_resume_data, updated_cv_text, updated_cv)
    updated_cv["ats_match_score"] = final_match["score"]

    print("\n=== Final ATS Analysis ===")
    print(f"Final ATS Score (Maximum Ethically Achievable): {final_match['score']}%")
    print(f"Matching Skills: {final_match['skill_matches']} / {final_match['total_skills']}")
    print(f"Matching Keywords: {final_match['keyword_matches']} / {final_match['total_keywords']}")
    print(f"Experience: {final_match['resume_years']} years (Job requires: {final_match['job_years']})")
    print("CV optimization process completed.")

    final_score = final_match['score']
    return updated_cv, initial_match, final_match, initial_score, final_score
