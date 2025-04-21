from pdfminer.high_level import extract_text
import openai
import streamlit as st
import json
from typing import Dict
import os
from src.models import JsonResume
import re
import time
from typing import Dict

import requests
from bs4 import BeautifulSoup, Comment

from dateutil import parser
from datetime import datetime

import copy


client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"]
)

def run_llm(prompt, temperature=0.0):
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-lite-001",
            messages=[
                {"role": "system", "content": "You are an expert assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            top_p=0.000001,
        )
        if not response.choices or len(response.choices) == 0:
            print("LLM returned empty choices")
            return None
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in LLM call: {e}")
        return None

    

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

def run_llm_cv_creation(prompt, temperature=0.9):
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-lite-001",
            messages=[
                {"role": "system", "content": "You are an expert assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            top_p=1,
            seed=42,
        )
        if not response.choices or len(response.choices) == 0:
            print("LLM returned empty choices")
            return None
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in LLM call: {e}")
        return None

def scrape_job_description(url: str) -> str:
    """
    Extracts all text from a job posting URL and uses an LLM agent to clean and extract the job description.

    Args:
        url (str): The URL of the job posting.

    Returns:
        str: The extracted and cleaned job description.

    Raises:
        requests.RequestException: If the HTTP request fails (e.g., 403, 404, timeout).
        ValueError: If the LLM fails to return a valid response or if the content is not a job posting.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Lanza una excepción para códigos de estado 4xx/5xx

        # Parsear el HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Eliminar etiquetas no deseadas
        for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form", "iframe"]):
            tag.decompose()

        # Eliminar comentarios HTML
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Extraer todo el texto visible del body (sin filtrar por candidatos)
        if soup.body:
            content = soup.body
        else:
            content = soup  # Si no hay body, tomar todo el soup

        plain_text = content.get_text(separator="\n", strip=True)

        print(f"[DEBUG] Full content length: {len(plain_text)}")
        print(f"[DEBUG] Full content starts with: {plain_text[:100]}")

        # Guardar el texto completo en un archivo
        try:
            with open("job_description_full.txt", "w", encoding="utf-8") as f:
                f.write(plain_text)
            print("Saved job_description_full.txt successfully.")
        except Exception as e:
            print(f"Error saving job_description_full.txt: {e}")

        # Prompt para el LLM
        prompt = f"""
        Extract the job description from the following text. Ignore menus, footers, ads, and any irrelevant content.

        If this is not a job posting, respond with exactly: "ERROR: Not a job posting".

        Return the job description with all relevant information about the role included (Skills, job title, company name, location, etc.) without any additional comments:

        \"\"\"
        {plain_text}
        \"\"\"
        """

        # Ejecutar el LLM con reintentos
        max_retries = 3
        for attempt in range(max_retries):
            result = run_llm(prompt)  # Asumo que run_llm está definido en otro lugar
            print("LLM response (job_scraper):")
            print(result)
            with open("file_outputs/job_description_llm_output.txt", "w", encoding="utf-8") as f:
                f.write(result)

            if not result or not result.strip():
                print(f"LLM returned empty response. Retry {attempt+1}/{max_retries}...")
                time.sleep(60)
            elif result.strip() == "ERROR: Not a job posting":
                raise ValueError("The provided URL does not contain a valid job posting")
            else:
                break  # Salir del bucle si hay resultado válido
        else:
            raise ValueError("LLM failed to return a valid response after maximum retries")

        return result.strip()

    except requests.RequestException as e:
        raise requests.RequestException(f"Failed to fetch job posting from {url}: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing job description: {str(e)}")






def extract_cv_text(pdf_path: str) -> str:
    """
    Extracts text from a PDF CV file using pdfminer.six.
    """
    try:
        text = extract_text(pdf_path)
        with open("description.txt", 'w', encoding='utf-8') as archivo:
            archivo.writelines(text)
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

def extract_job_description_data(text: str, is_job: bool = True) -> Dict:
    """
    Extracts keywords from the provided job description or resume that are relevant for Applicant Tracking Systems (ATS).

    Args:
        text (str): The job description or resume text to extract keywords from.
        is_job (bool, optional): Whether the text is a job description (True) or a resume (False). Defaults to True.

    Returns:
        Dict: A dictionary containing a list of extracted keywords under the key 'keywords'.
    """
    print("Extracting structured data from " + ("job description" if is_job else "CV") + "...")

    # Prompt building
    common_instructions = """
        1. Include specific technical tools (e.g., 'Tableau', 'Google Analytics'), programming languages (e.g., 'Python', 'SQL'), or frameworks (e.g., 'TensorFlow', 'React').
        2. Include soft skills (e.g., 'communication', 'teamwork', 'leadership').
        3. Include techniques or methodologies (e.g., 'machine learning', 'A/B testing', 'scrum').
        4. Include industry-specific terms or standards (e.g., 'game economy', 'GDPR', 'HIPAA'), but ONLY if they describe a concept, standard, or domain knowledge, not a metric.
        5. EXCLUDE ALL business metrics (e.g., 'DAU', 'ARPU', 'LTV', 'churn rate', 'ROI', 'CTR', 'NPV', 'KPI', 'bounce rate', 'EBITDA').
        6. For each potential keyword, follow this reasoning process:
           (a) Identify the term in the text.
           (b) Check if it matches known metrics (e.g., 'DAU', 'LTV', 'ROI', 'KPI'); if yes, exclude it and stop.
           (c) Determine if it is a technical tool, language, framework, soft skill, technique, or industry term; if yes, proceed.
           (d) Ensure it is not a vague term (e.g., 'data', 'business', 'analytics') unless part of a specific name (e.g., 'Google Analytics'); if vague, exclude it.
           (e) If the term passes all checks, include it in the output.
        7. Only extract explicit terms; do not infer or combine terms.
    """

    examples = """
        8. Examples across industries:
           - Text: 'Requires Python, SQL, Tableau, DAU, and teamwork in gaming.'
             Output: {"keywords": ["Python", "SQL", "Tableau", "teamwork"]}
           - Text: 'Must know Excel, Power BI, A/B testing, ROI, and communication in finance.'
             Output: {"keywords": ["Excel", "Power BI", "A/B testing", "communication"]}
           - Text: 'Needs Java, Docker, GDPR, DevOps, and leadership in tech.'
             Output: {"keywords": ["Java", "Docker", "GDPR", "DevOps", "leadership"]}
           - Text: 'Requires R, SQL, HIPAA, machine learning, and teamwork in healthcare.'
             Output: {"keywords": ["R", "SQL", "HIPAA", "machine learning", "teamwork"]}
           - Text: 'Must know Google Ads, SEO, CTR, and collaboration in marketing.'
             Output: {"keywords": ["Google Ads", "SEO", "collaboration"]}
           - Text: 'Needs C++, ROS, agile, and problem-solving in robotics.'
             Output: {"keywords": ["C++", "ROS", "agile", "problem-solving"]}
           - Text: 'Requires SAS, SPSS, predictive analytics, and adaptability in data science.'
             Output: {"keywords": ["SAS", "SPSS", "predictive analytics", "adaptability"]}
           - Text: 'Must know Salesforce, CRM, KPI, and negotiation in sales.'
             Output: {"keywords": ["Salesforce", "CRM", "negotiation"]}
           - Text: 'Needs AWS, Kubernetes, game economy, and teamwork in gaming.'
             Output: {"keywords": ["AWS", "Kubernetes", "game economy", "teamwork"]}
           - Text: 'Requires VBA, Tableau, NPV, and strategic thinking in consulting.'
             Output: {"keywords": ["VBA", "Tableau", "strategic thinking"]}
    """

    prompt_type = "job description" if is_job else "Resume"
    prompt = f"""
        Extract keywords from the provided {prompt_type} that are relevant for Applicant Tracking Systems (ATS). 
        Follow these rules:
        {common_instructions}
        {examples}

        Text:
        \"\"\"
        {text}
        \"\"\"

        Return ONLY a JSON object with the key 'keywords' containing a list of extracted keywords.
    """

    # LLM call with retries
    max_retries = 3
    for attempt in range(max_retries):
        result = run_llm(prompt)
        print("LLM response (cv_parser):")
        print(result)

        filename = "file_outputs/job_summary_llm_output.txt" if is_job else "file_outputs/cv_summary_llm_output.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result)

        if not result or not result.strip():
            print(f"LLM returned empty response. Retry {attempt + 1}/{max_retries}...")
            time.sleep(60)

    print("LLM response (job_to_cv_parser):")
    print(result)

    # Extract JSON block
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

def parse_to_json_resume_sync(text: str) -> Dict:
    """
    Parses CV text into JSON Resume format using an LLM via OpenRouter with pydantic-ai.
    """
    prompt = f"""
    You are an expert in CV parsing.

    Take the following extracted CV text, which may have mixed sections (e.g., Profile and Experience blended due to layout issues), and structure it into the JSON Resume standard format.

    Separate clearly the "Profile" (summary) from "Professional Experience" (work history with dates and descriptions) and other sections like Education, Skills, Languages, and Projects.

    Don't return sumamry for experience, just the higjhlights.

    Preserve the original content without adding or modifying information beyond structuring.

    Here is the JSON Resume schema for reference:
    - basics: {{"name": "string", "label": "string", "email": "string", "phone": "string", "url": "string|null", "summary": "string|null", "location": {{"address": "string|null", "postalCode": "string|null", "city": "string|null", "countryCode": "string|null", "region": "string|null"}}|null, "profiles": [{{"network": "string", "username": "string", "url": "string|null"}}]}}
    - work: [{{"company": "string", "position": "string", "website": "string|null", "startDate": "string|null", "endDate": "string|null", "summary": "string|null", "highlights": ["string"]}}]
    - education: [{{"institution": "string", "area": "string|null", "studyType": "string|null", "startDate": "string|null", "endDate": "string|null", "score": "string|null", "courses": ["string"]}}]
    - skills: [{{"name": "string", "level": "string|null", "keywords": ["string"]}}]
    - languages: [{{"language": "string", "fluency": "string|null"}}]
    - projects: [{{"name": "string", "description": "string|null", "highlights": ["string"], "keywords": ["string"], "startDate": "string|null", "endDate": "string|null", "url": "string|null", "roles": ["string"], "entity": "string|null", "type": "string|null"}}]

    Important rules:
    1. For URL fields (url, website), always use full URLs starting with "http://" or "https://". If a URL is relative, missing, or invalid, set the field to null.
    2. For the location field inside basics, if any location sub-field (address, postalCode, city, countryCode, region) is missing or empty, set the entire location field to null. Do not use empty strings for any location sub-fields.
    3. If any field is missing or cannot be extracted from the provided text, set that field to null. Do not use empty strings.
    4. Return the result as a valid JSON object wrapped in ```json ``` markers.

    CV Text:
    \"\"\"
    {text}
    \"\"\"
    
    Return the result as a JSON object wrapped in ```json ``` markers.
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Llamada al LLM
            result = run_llm(prompt)
            print("LLM response (cv_parser):")
            print(result)
            with open("file_outputs/job_standar_llm_output.txt", 'w', encoding='utf-8') as f:
                f.write(result)

            # Verificar si la respuesta está vacía
            if not result or not result.strip():
                print(f"LLM returned empty response. Retry {attempt+1}/{max_retries}...")
                time.sleep(3)
                continue

            # Extraer el JSON de la respuesta
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
            else:
                json_str = result.strip()  # Asumimos que es JSON puro si no hay marcadores

            # Parsear el JSON
            json_cv = json.loads(json_str)
            print(f"Parsed JSON before preprocessing: {json_cv}")

            # Validación básica para asegurar que sigue el formato JSON Resume
            if not isinstance(json_cv, dict) or "basics" not in json_cv:
                raise ValueError("Parsed JSON does not follow JSON Resume format")

            # Ajustar campos según las reglas
            if "basics" in json_cv and "location" in json_cv["basics"]:
                location = json_cv["basics"]["location"]
                # Solo intentamos ajustar si location no es None
                if location is not None:
                    if not any(location.get(field) for field in ["address", "postalCode", "city", "countryCode", "region"]):
                        json_cv["basics"]["location"] = None

            return json_cv  # Éxito, devolvemos el JSON

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM output as JSON: {e}")
            print("Raw LLM output:")
            print(result)
            if attempt < max_retries - 1:
                print(f"Retrying LLM call ({attempt+1}/{max_retries})...")
                time.sleep(3)
                continue
            else:
                raise ValueError("Failed to parse LLM output as JSON after retries")
        except Exception as e:
            print(f"Unexpected error during parsing: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying LLM call ({attempt+1}/{max_retries})...")
                time.sleep(3)
                continue
            else:
                raise ValueError(f"Failed to process CV text after retries: {e}")

    raise ValueError("Failed to parse CV text after all retries")

def match_with_llm(cv_items: list, job_items: list) -> dict:
    """
    Uses an LLM to match  keywords between CV and job offer.
    
    Args:
        cv_items (list): List of items from the CV (keywords).
        job_items (list): List of items from the job offer (keywords).
        
    
    Returns:
        dict: JSON with matches and missing items.
    """
    prompt = (
        f"You are an expert in job keywordsanalysis. I have two lists of keywords :\n\n"
        f" from CV: {cv_items}\n"
        f" from job offer: {job_items}\n\n"
        "Your task is:\n"
        "1. Identify which {item_type} from the CV match those from the job offer, considering synonyms, context, and equivalences (e.g., Power BI can match with data visualization tools (Tableau, Looker, Power BI, etc.)).\n"
        "2. List the {item_type} from the job offer that are missing from the CV.\n\n"
        "Rules:\n"
        "- Be flexible with language: ignore minor formatting or wording differences.\n"
        "- Do not invent items that are not explicitly in the lists.\n"
        "- Use only the provided lists, do not assume additional information.\n\n"
        "- NOT include languages if there is more skills\n\n" 
        "Return the result as a JSON object with two keys: \"matches\" and \"missing\", like this:\n"
        "- \"matches\": a list of matching items\n"
        "- \"missing\": a list of items from the job offer not found in the CV\n\n"
        "Example output:\n"
        "```json\n"
        "{\"matches\": [\"SQL\", \"Python\"], \"missing\": [\"Tableau\"]}\n"

        "```"
    )

    # Llamada al LLM (ajusta run_llm según tu API o implementación)
    result = run_llm(prompt)
    
    print("LLM response (match_with_llm):",result)

    # Extraer JSON de la respuesta
    try:
        if '```json' in result:
            json_str = result.split('```json')[1].split('```')[0].strip()
        else:
            json_str = result.strip()
        match_data = json.loads(json_str)
        return match_data
    except (json.JSONDecodeError, IndexError) as e:
        print(f'Error parsing LLM response for {item_type}: {e}')
        print('Raw LLM output:', result)
        return {
            'matches': [],
            'missing': job_items
        }

def calculate_ats_score( keywords_match: dict,total_job_keywords: int) -> float:
    """
    Calculate the ATS score based on matches for  keywords

    - Keywords: 
    
    -

    Args:
        keywords_match (dict): Dictionary with 'matches' and 'missing' for keywords.
        
        total_job_keywords (int): Total number of keywords required in the job offer.
        

    Returns:
        float: ATS score as a percentage (0-100).
    """
   
    keyword_matches = len(keywords_match.get('matches', []))

    # Calculate match percentages
    
    keywords_percentage = (keyword_matches / total_job_keywords) if total_job_keywords > 0 else 0

    # Apply weights: 65% keywords, 35% skills
    score =  keywords_percentage

    # Return score as percentage
    return round(score * 100, 2)


def adapt_cv_with_llm(original_cv: dict, job_data: dict, keywords_match: dict) -> dict:
    """
    Adapts the original CV to improve ATS score by incorporating matched and inferred skills/keywords.

    Args:
        original_cv (dict): Original CV in JSON Resume format.
                
        keywords_match (dict): Dictionary with 'matches' and 'missing' for keywords.

    Returns:
        dict: Adapted CV in JSON Resume format, validated with Pydantic.
    """
    # Depuración: Imprimir los argumentos para verificar su estructura
    print("Debugging adapt_cv_with_llm inputs:")
    print("original_cv:", json.dumps(original_cv, indent=2))
    print("job_data:", json.dumps(job_data, indent=2))
    
    print("keywords_match:", json.dumps(keywords_match, indent=2))

    # Validar que los argumentos tengan la estructura esperada
    if not isinstance(original_cv, dict):
        raise ValueError("original_cv must be a dictionary")
    if not isinstance(job_data, dict):
        raise ValueError("job_data must be a dictionary")
  
    if not isinstance(keywords_match, dict) or 'matches' not in keywords_match or 'missing' not in keywords_match:
        raise ValueError("keywords_match must be a dictionary with 'matches' and 'missing' keys")

    # Asegurarnos de que las listas contengan solo strings
  
    job_keywords = [str(item) for item in job_data.get('keywords', [])]
    
    matched_keywords = [str(item) for item in keywords_match.get('matches', [])]
    missing_keywords = [str(item) for item in keywords_match.get('missing', [])]


    prompt = f"""
    You are an expert in CV optimization for Applicant Tracking Systems (ATS). I have an original CV and a job offer:

    Original CV (JSON Resume format):
    {json.dumps(original_cv, indent=2)}

    Job Offer:
    - Keywords: {json.dumps(job_keywords)}

    Matches:
    - Keywords matched: {json.dumps(matched_keywords)}

    Missing:
    - Keywords missing: {json.dumps(missing_keywords)}

    Your task is:
    1. Adapt the CV to achieve at least 90% keyword matching for ATS by:
        (a) Including all matched keywords in 'summary', 'work.experience[].highlights', and 'skills' to maximize density.
        (b) Adding ALL missing keywords unless clearly unrelated to the job domain (e.g., exclude 'Firebase' for non-mobile roles), using this Chain of Thought:
            - Step 1: List matched keywords and missing keywords.
            - Step 2: Add every missing keyword to 'skills', assuming it fits the general job domain (e.g., 'Tableau', 'AWS' for data/tech roles).
            - Step 3: Update 'summary' and 'work.highlights' to include all added keywords.
            - Step 4: Verify only that keywords align broadly with the domain; include unless obviously irrelevant.
        (c) Reorganizing content:
            - List all keywords (matched and added) first in 'skills'.
            - Rewrite 'summary' with 8-12 keywords.
            - Update 'work.experience[].highlights' with 4-5 highlights per role using keywords.
            - Repeat keywords across sections for ATS parsing.
    2. Return the adapted CV in JSON Resume format, ensuring schema compliance.

    Rules:
    - Include ALL missing keywords to reach 90% coverage, assuming they fit the job domain.
    - Use exact job keywords for ATS matching.
    - Avoid vague terms (e.g., 'expert') unless in the offer.
    - Format 'skills' as {{"name": "Skill", "level": null, "keywords": []}}.
    - Use temperature=1.0, top-k=1, seed=42 for maximum keyword inclusion.

    Examples:
    1. Gaming Analyst:
        - CV: {{"skills": [{{"name": "Python"}}, {{"name": "SQL"}}], "work": [{{"highlights": ["Wrote Python scripts."]}}], "summary": "Data analyst."}}
        - Keywords: ["Python", "SQL", "Tableau", "machine learning", "teamwork", "data analysis", "game economy", "BigQuery", "A/B testing", "predictive analytics", "Google Analytics", "Looker", "AWS"]
        - Matched: ["Python", "SQL"]
        - Missing: ["Tableau", "machine learning", "teamwork", "data analysis", "game economy", "BigQuery", "A/B testing", "predictive analytics", "Google Analytics", "Looker", "AWS"]
        - Adapted CV (partial):
            ```json
            {{
            "summary": "Data analyst skilled in Python, SQL, Tableau, machine learning, A/B testing, predictive analytics, teamwork, game economy, BigQuery, Google Analytics, Looker, AWS.",
            "skills": [{{"name": "Python"}}, {{"name": "SQL"}}, {{"name": "Tableau"}}, {{"name": "Machine Learning"}}, {{"name": "A/B Testing"}}, {{"name": "Predictive Analytics"}}, {{"name": "Teamwork"}}, {{"name": "Game Economy"}}, {{"name": "BigQuery"}}, {{"name": "Google Analytics"}}, {{"name": "Looker"}}, {{"name": "AWS"}}],
            "work": [{{"highlights": ["Developed Python scripts for machine learning and A/B testing.", "Used Tableau, BigQuery, Looker for data analysis.", "Collaborated on game economy with Google Analytics.", "Leveraged AWS for predictive analytics.", "Applied teamwork in projects."]}}]
            }}
            ```
            Reasoning: Added all missing keywords as they fit data/gaming domain.
    2. Finance Analyst:
        - CV: {{"skills": [{{"name": "Excel"}}], "work": [{{"highlights": ["Analyzed financial data."]}}], "summary": "Finance professional."}}
        - Keywords: ["Excel", "Power BI", "financial modeling", "communication", "strategic thinking", "data visualization", "Tableau", "predictive analytics", "AWS", "Looker"]
        - Matched: ["Excel"]
        - Missing: ["Power BI", "financial modeling", "communication", "strategic thinking", "data visualization", "Tableau", "predictive analytics", "AWS", "Looker"]
        - Adapted CV (partial):
            ```json
            {{
            "summary": "Finance professional skilled in Excel, Power BI, financial modeling, data visualization, Tableau, communication, strategic thinking, predictive analytics, Looker.",
            "skills": [{{"name": "Excel"}}, {{"name": "Power BI"}}, {{"name": "Financial Modeling"}}, {{"name": "Data Visualization"}}, {{"name": "Tableau"}}, {{"name": "Communication"}}, {{"name": "Strategic Thinking"}}, {{"name": "Predictive Analytics"}}, {{"name": "Looker"}}],
            "work": [{{"highlights": ["Performed financial modeling with Excel and Power BI.", "Created data visualizations with Tableau and Looker.", "Communicated strategic insights.", "Supported predictive analytics.", "Applied strategic thinking."]}}]
            }}
            ```
            Reasoning: Added all missing keywords except 'AWS' (less relevant to finance).
    3. Healthcare Data:
        - CV: {{"skills": [{{"name": "R"}}], "work": [{{"highlights": ["Conducted statistical analysis."]}}], "summary": "Data scientist."}}
        - Keywords: ["R", "SQL", "machine learning", "predictive analytics", "teamwork", "statistical analysis", "BigQuery", "Tableau", "Google Analytics", "AWS"]
        - Matched: ["R"]
        - Missing: ["SQL", "machine learning", "predictive analytics", "teamwork", "statistical analysis", "BigQuery", "Tableau", "Google Analytics", "AWS"]
        - Adapted CV (partial):
            ```json
            {{
            "summary": "Data scientist proficient in R, SQL, statistical analysis, machine learning, predictive analytics, teamwork, BigQuery, Tableau, Google Analytics, AWS.",
            "skills": [{{"name": "R"}}, {{"name": "SQL"}}, {{"name": "Statistical Analysis"}}, {{"name": "Machine Learning"}}, {{"name": "Predictive Analytics"}}, {{"name": "Teamwork"}}, {{"name": "BigQuery"}}, {{"name": "Tableau"}}, {{"name": "Google Analytics"}}, {{"name": "AWS"}}],
            "work": [{{"highlights": ["Conducted statistical analysis with R and SQL.", "Built machine learning models with BigQuery.", "Used Tableau and Google Analytics for insights.", "Collaborated with teamwork.", "Deployed on AWS."]}}]
            }}
            ```
            Reasoning: Added all missing keywords as they fit data science domain.

    Output:
    Return the full adapted CV as a JSON object, enclosed in ```json``` markers.
    ```json
    {{"basics": {{"name": "Example", ...}}, ...}}
        """



    print("Estamos dentro de la funcion:")
    print(original_cv)
    print(type(original_cv))
    print(job_data)
    print(type(job_data))
    print(keywords_match)
    print(type(keywords_match))
   

    # Llamada al LLM (ajusta según tu implementación)
    result = run_llm(prompt)  # Asume run_llm está definido

    try:
        # Parsear la respuesta del LLM
        if '```json' in result:
            json_str = result.split('```json')[1].split('```')[0].strip()
        else:
            json_str = result.strip()
        adapted_cv = json.loads(json_str)

        # Validar con Pydantic
        validated_cv = JsonResume(**adapted_cv)
        return validated_cv.dict(exclude_unset=True)
    except (json.JSONDecodeError, IndexError, ValueError) as e:
        print(f"Error parsing LLM response for CV adaptation: {e}")
        print("Raw LLM output:", result)
        # Devolver el CV original como fallback
        return original_cv

import os
import yaml
from datetime import datetime
import re

import subprocess
import glob
import shutil





import os
import yaml
from datetime import datetime
import re

def safe_string(value, default=""):
    """Converts a value to a string, handling None and non-string types."""
    if value is None:
        return default
    return str(value).strip()

def is_valid_label(label):
    """Validates a label (min 3 chars, allows most characters)."""
    label = safe_string(label)
    if not label:
        print(f"Debug: Label '{label}' descartado: vacío o None")
        return False
    pattern = r'^[\w\s\-\&\#]{3,}$'
    if re.match(pattern, label):
        print(f"Debug: Label '{label}' es válido")
        return True
    print(f"Debug: Label '{label}' descartado: no cumple con el formato (mínimo 3 caracteres, letras, números, espacios, -, &, #)")
    return False

def is_valid_email(email):
    """Validates an email address."""
    email = safe_string(email)
    if not email:
        print(f"Debug: Email '{email}' descartado: vacío o None")
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        print(f"Debug: Email '{email}' es válido")
        return True
    print(f"Debug: Email '{email}' descartado: formato inválido")
    return False

def is_valid_phone_number(phone):
    """Validates a phone number, requiring country code or clear separators."""
    phone = safe_string(phone)
    if not phone:
        print(f"Debug: Teléfono '{phone}' descartado: vacío o None")
        return False
    # Patrón estricto: permite números continuos con código de país, o formatos con separadores
    pattern = r'^(\+\d{1,3}[-.\s])\d{9,12}$|^(\+\d{1,3}[-.\s])(\d{3,4}[-.\s]\d{3,4}[-.\s]\d{3,4})$|^(\(\d{3,4}\)\s\d{3,4}[-.\s]\d{3,4})$|^(\d{3,4}[-.\s]\d{3,4}[-.\s]\d{3,4})$'
    if re.match(pattern, phone):
        print(f"Debug: Teléfono '{phone}' es válido")
        return True
    print(f"Debug: Teléfono '{phone}' descartado: formato inválido (requiere código de país con separador, paréntesis con espacio, o separadores claros)")
    return False

def is_valid_url(url):
    """Validates a URL (must start with http:// or https://)."""
    url = safe_string(url)
    if not url:
        print(f"Debug: URL '{url}' descartado: vacío o None")
        return False
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    if re.match(pattern, url):
        print(f"Debug: URL '{url}' es válido")
        return True
    print(f"Debug: URL '{url}' descartado: formato inválido (debe comenzar con http:// o https://)")
    return False

def is_valid_summary(summary):
    """Validates a summary (min 10 chars)."""
    summary = safe_string(summary)
    if not summary or len(summary) < 10:
        print(f"Debug: Resumen '{summary}' descartado: demasiado corto o vacío (mínimo 10 caracteres)")
        return False
    print(f"Debug: Resumen es válido (longitud: {len(summary)})")
    return True

def is_valid_location(location):
    """Validates a location (at least one non-null field)."""
    if not isinstance(location, dict):
        print(f"Debug: Ubicación '{location}' descartada: no es un diccionario")
        return False
    fields = ["address", "postalCode", "city", "countryCode", "region"]
    has_valid_field = any(safe_string(location.get(field)) for field in fields)
    if has_valid_field:
        print(f"Debug: Ubicación '{location}' es válida")
        return True
    print(f"Debug: Ubicación '{location}' descartada: no tiene campos válidos")
    return False

def normalize_social_network(network):
    """Normalizes social network names to RenderCV-compatible values."""
    network = safe_string(network)
    if not network:
        print(f"Debug: Red social '{network}' descartada: vacía o None")
        return None
    valid_networks = [
        'LinkedIn', 'GitHub', 'GitLab', 'Instagram', 'ORCID', 'Mastodon',
        'StackOverflow', 'ResearchGate', 'YouTube', 'Google Scholar', 'Telegram', 'X'
    ]
    network_map = {
        'linkedin': 'LinkedIn',
        'linkedin.com': 'LinkedIn',
        'www.linkedin.com': 'LinkedIn',
        'github': 'GitHub',
        'github.com': 'GitHub',
        'www.github.com': 'GitHub',
        'gitlab': 'GitLab',
        'gitlab.com': 'GitLab',
        'instagram': 'Instagram',
        'instagram.com': 'Instagram',
        'orcid': 'ORCID',
        'orcid.org': 'ORCID',
        'mastodon': 'Mastodon',
        'mastodon.social': 'Mastodon',
        'stackoverflow': 'StackOverflow',
        'stackoverflow.com': 'StackOverflow',
        'researchgate': 'ResearchGate',
        'researchgate.net': 'ResearchGate',
        'youtube': 'YouTube',
        'youtube.com': 'YouTube',
        'googlescholar': 'Google Scholar',
        'scholar.google.com': 'Google Scholar',
        'telegram': 'Telegram',
        't.me': 'Telegram',
        'twitter': 'X',
        'twitter.com': 'X',
        'x.com': 'X'
    }
    normalized = network_map.get(network.lower(), network.capitalize())
    if normalized in valid_networks:
        print(f"Debug: Red social '{network}' normalizada a '{normalized}'")
        return normalized
    print(f"Debug: Red social '{network}' descartada: no es una red válida")
    return None

def preprocess_json(data):
    """Preprocesses JSON data to clean and validate fields."""
    if isinstance(data, dict):
        new_data = {}
        if "basics" in data:
            new_data["basics"] = {}
        for k, v in data.items():
            if isinstance(v, str):
                if k == "name":
                    if safe_string(v):
                        print(f"Debug: Nombre '{v}' incluido (sin validación)")
                        new_data[k] = v
                    else:
                        print(f"Debug: Nombre '{v}' descartado: vacío o None")
                        new_data[k] = None
                elif k == "label":
                    new_data[k] = v if is_valid_label(v) else None
                elif k == "email":
                    new_data[k] = v if is_valid_email(v) else None
                elif k == "phone":
                    if is_valid_phone_number(v):
                        new_data[k] = v
                    else:
                        print(f"Debug: Teléfono '{v}' descartado en preprocess_json: inválido")
                        new_data[k] = None
                elif k in ("url", "website"):
                    if v.strip() == "" or v.strip() is None:
                        print(f"Debug: URL '{v}' descartado: vacío o None")
                        new_data[k] = None
                    elif is_valid_url(v):
                        new_data[k] = v
                    else:
                        new_data[k] = "https://" + v.lstrip("/") if not v.startswith("http") else None
                elif k == "summary":
                    new_data[k] = v if is_valid_summary(v) else None
                else:
                    new_data[k] = v
            elif k == "location" and isinstance(v, dict):
                new_data[k] = v if is_valid_location(v) else None
            elif k == "profiles" and isinstance(v, list):
                valid_profiles = []
                for profile in v:
                    if not isinstance(profile, dict):
                        print(f"Debug: Perfil '{profile}' descartado: no es un diccionario")
                        continue
                    network = safe_string(profile.get("network"))
                    username = safe_string(profile.get("username"))
                    profile_url = safe_string(profile.get("url"))
                    if network and username:
                        normalized_network = normalize_social_network(network)
                        if normalized_network and (is_valid_url(profile_url) or not profile_url):
                            valid_profiles.append({
                                "network": normalized_network,
                                "username": username,
                                "url": profile_url if is_valid_url(profile_url) else None
                            })
                        else:
                            print(f"Debug: Perfil '{network}/{username}' descartado: red o URL inválidos")
                    else:
                        print(f"Debug: Perfil '{network}/{username}' descartado: falta red o usuario")
                new_data[k] = valid_profiles
            elif isinstance(v, (dict, list)):
                new_data[k] = preprocess_json(v)
            else:
                new_data[k] = v
        return new_data
    elif isinstance(data, list):
        return [preprocess_json(item) for item in data]
    else:
        return data

def replace_null_strings(data):
    """Replaces None values with appropriate defaults, preserving None for basics fields."""
    list_fields = {"profiles", "highlights", "courses", "keywords", "roles"}
    if isinstance(data, dict):
        for k, v in data.items():
            if k in ("name", "label", "email", "phone", "url", "summary", "location", "profiles"):
                continue
            elif k in list_fields:
                if v is None or v == "":
                    data[k] = []
                elif isinstance(v, (dict, list)):
                    replace_null_strings(v)
            elif v is None:
                data[k] = ""
            elif isinstance(v, (dict, list)):
                replace_null_strings(v)
    elif isinstance(data, list):
        for item in data:
            replace_null_strings(item)
    return data

def convert_date(date_str):
    """Converts a date string to RenderCV-compatible format (YYYY-MM-DD, YYYY-MM, YYYY) or None if invalid."""
    date_str = safe_string(date_str)
    if not date_str:
        print(f"Debug: Fecha '{date_str}' descartada: vacía o None")
        return None
    
    month_map = {
        'jan': '01', 'january': '01', 'enero': '01', 'ene': '01',
        'feb': '02', 'february': '02', 'febrero': '02',
        'mar': '03', 'march': '03', 'marzo': '03',
        'apr': '04', 'april': '04', 'abril': '04',
        'may': '05', 'mayo': '05',
        'jun': '06', 'june': '06', 'junio': '06',
        'jul': '07', 'july': '07', 'julio': '07',
        'aug': '08', 'august': '08', 'agosto': '08', 'ago': '08',
        'sep': '09', 'september': '09', 'septiembre': '09', 'sept': '09',
        'oct': '10', 'october': '10', 'octubre': '10',
        'nov': '11', 'november': '11', 'noviembre': '11',
        'dec': '12', 'december': '12', 'diciembre': '12', 'dic': '12'
    }

    try:
        # Normalizar espacios: reemplazar múltiples espacios/tabs por un solo espacio
        date_str = re.sub(r'\s+', ' ', date_str.strip().lower())
        print(f"Debug: Procesando fecha normalizada: '{date_str}'")
        
        if re.match(r'^\d{4}$', date_str):
            return f"{date_str}-01-01"
        if re.match(r'^\d{1,2}[/-]\d{4}$', date_str):
            month, year = re.split(r'[/-]', date_str)
            month = month.zfill(2)
            return f"{year}-{month}-01"
        if re.match(r'^\d{4}-\d{1,2}(-\d{1,2})?$', date_str):
            parts = date_str.split('-')
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1]}-01"
            elif len(parts) == 3:
                return date_str
        match = re.match(r'([a-z]+)\.?\s+(\d{4})', date_str)
        if match:
            month_str, year = match.groups()
            month = month_map.get(month_str)
            if month:
                print(f"Debug: Fecha '{date_str}' mapeada a '{year}-{month}-01'")
                return f"{year}-{month}-01"
            else:
                print(f"Debug: Fecha '{date_str}' descartada: mes '{month_str}' no reconocido")
                return None
        if re.match(r'^\d{4}/\d{1,2}$', date_str):
            year, month = date_str.split('/')
            month = month.zfill(2)
            return f"{year}-{month}-01"
        if date_str in ('present', 'actualidad'):
            print(f"Debug: Fecha '{date_str}' mapeada a 'present'")
            return "present"
        print(f"Debug: Fecha '{date_str}' descartada: formato inválido")
        return None
    except Exception as e:
        print(f"Debug: Error al parsear fecha '{date_str}': {e}, descartada")
        return None

def get_degree_abbreviation(study_type):
    """Converts a studyType value to a 3-letter abbreviation for degree."""
    study_type = safe_string(study_type).lower()
    degree_map = {
        'bachelor': 'DEG',
        'bsc': 'DEG',
        'ba': 'DEG',
        'bs': 'DEG',
        'undergraduate': 'DEG',
        'grado': 'DEG',
        'licenciatura': 'DEG',
        'master': 'POS',
        'msc': 'POS',
        'ma': 'POS',
        'postgraduate': 'POS',
        'postgrado': 'POS',
        'phd': 'DOC',
        'doctorate': 'DOC',
        'doctoral': 'DOC',
        'doctorado': 'DOC'
    }
    abbreviation = degree_map.get(study_type, 'DEG')
    print(f"Debug: Mapeando studyType '{study_type}' a abreviatura de grado '{abbreviation}'")
    if len(abbreviation) != 3:
        print(f"Debug: Abreviatura de grado '{abbreviation}' no tiene 3 letras, usando 'DEG'")
        return 'DEG'
    return abbreviation

def convert_to_rendercv(adapted_cv: dict, output_dir: str = "rendercv_output", theme: str = "classic") -> str:
    """
    Converts a JSON Resume formatted CV to a RenderCV-compatible YAML file.
    """
    if not isinstance(adapted_cv, dict):
        raise ValueError("adapted_cv must be a dictionary in JSON Resume format")
    
    if not isinstance(adapted_cv.get("basics", {}), dict):
        print("Debug: 'basics' no es un diccionario, usando diccionario vacío")
        adapted_cv["basics"] = {}
    if not isinstance(adapted_cv.get("work", []), list):
        print("Debug: 'work' no es una lista, usando lista vacía")
        adapted_cv["work"] = []
    if not isinstance(adapted_cv.get("education", []), list):
        print("Debug: 'education' no es una lista, usando lista vacía")
        adapted_cv["education"] = []
    if not isinstance(adapted_cv.get("skills", []), list):
        print("Debug: 'skills' no es una lista, usando lista vacía")
        adapted_cv["skills"] = []
    if not isinstance(adapted_cv.get("projects", []), list):
        print("Debug: 'projects' no es una lista, usando lista vacía")
        adapted_cv["projects"] = []
    if not isinstance(adapted_cv.get("languages", []), list):
        print("Debug: 'languages' no es una lista, usando lista vacía")
        adapted_cv["languages"] = []

    rendercv_data = {
        "cv": {
            "name": "",
            "sections": {}
        },
        "design": {
            "theme": theme,
            "page": {
                "size": "us-letter",
                "top_margin": "2cm",
                "bottom_margin": "2cm",
                "left_margin": "2cm",
                "right_margin": "2cm",
                "show_page_numbering": True,
                "show_last_updated_date": True
            },
            "section_titles": {
                "vertical_space_above": "1cm",
                "vertical_space_below": "0.7cm"
            },
            "entries": {
                "vertical_space_between_entries": "2.5em"
            }
        },
        "locale": {
            "language": "en"
        },
        "rendercv_settings": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "bold_keywords": []
        }
    }

    basics = adapted_cv.get("basics", {})
    cv = rendercv_data["cv"]
    
    name = safe_string(basics.get("name"))
    print(f"Debug: Procesando nombre en convert_to_rendercv: '{name}'")
    if name:
        cv["name"] = name
    else:
        cv["name"] = "Unknown"
        print("Debug: Nombre descartado: vacío o None, usando 'Unknown'")

    email = safe_string(basics.get("email"))
    print(f"Debug: Procesando email en convert_to_rendercv: '{email}'")
    if is_valid_email(email):
        cv["email"] = email
    else:
        print(f"Debug: Email '{email}' no incluido en YAML: inválido o None")

    phone = safe_string(basics.get("phone"))
    print(f"Debug: Procesando teléfono en convert_to_rendercv: '{phone}'")
    if phone and is_valid_phone_number(phone):
        cv["phone"] = phone
    else:
        print(f"Debug: Teléfono '{phone}' no incluido en YAML: inválido o None")

    website = safe_string(basics.get("url"))
    print(f"Debug: Procesando URL en convert_to_rendercv: '{website}'")
    if is_valid_url(website):
        cv["website"] = website
    else:
        print(f"Debug: URL '{website}' no incluido en YAML: inválido o None")

    location = basics.get("location", {})
    print(f"Debug: Procesando ubicación en convert_to_rendercv: '{location}'")
    if is_valid_location(location):
        location_parts = [
            safe_string(location.get("city")),
            safe_string(location.get("region")),
            safe_string(location.get("countryCode"))
        ]
        print(f"Debug: Valores de ubicación: city={location_parts[0]!r}, region={location_parts[1]!r}, countryCode={location_parts[2]!r}")
        non_empty_parts = [part for part in location_parts if part]
        cv["location"] = ",".join(non_empty_parts)
    else:
        print(f"Debug: Ubicación '{location}' no incluida en YAML: inválida o None")

    profiles = basics.get("profiles", [])
    print(f"Debug: Procesando perfiles en convert_to_rendercv: '{profiles}'")
    if not isinstance(profiles, list):
        print("Debug: 'profiles' no es una lista, usando lista vacía")
        profiles = []
    if profiles:
        social_networks = []
        for profile in profiles:
            if not isinstance(profile, dict):
                print(f"Debug: Perfil '{profile}' descartado: no es un diccionario")
                continue
            network = safe_string(profile.get("network"))
            username = safe_string(profile.get("username"))
            if network and username:
                normalized_network = normalize_social_network(network)
                if normalized_network:
                    social_networks.append({
                        "network": normalized_network,
                        "username": username
                    })
                else:
                    print(f"Debug: Perfil '{network}/{username}' descartado: red inválida")
            else:
                print(f"Debug: Perfil '{network}/{username}' descartado: falta red o usuario")
        if social_networks:
            cv["social_networks"] = social_networks
        else:
            print(f"Debug: No se incluyeron perfiles válidos en YAML")

    sections = cv["sections"]
    summary = safe_string(basics.get("summary"))
    print(f"Debug: Procesando resumen en convert_to_rendercv: '{summary[:50]}...'")
    if is_valid_summary(summary):
        sections["Summary"] = [summary]
    else:
        print(f"Debug: Resumen '{summary[:50]}...' no incluido en YAML: inválido o None")

    work = adapted_cv.get("work", [])
    if work:
        sections["Experience"] = []
        print("Debug: Fechas de experiencia laboral:")
        for job in work:
            if not isinstance(job, dict):
                print(f"Debug: Entrada de trabajo '{job}' descartada: no es un diccionario")
                continue
            print(f"Debug: Empresa: {job.get('company')}, startDate: {job.get('startDate')}, endDate: {job.get('endDate')}")
        for job in work:
            if not isinstance(job, dict):
                continue
            company = safe_string(job.get("company"), "Unknown")
            entry = {
                "company": company,
                "position": safe_string(job.get("position")),
                "location": safe_string(job.get("location")),
                "summary": safe_string(job.get("summary")),
                "highlights": [safe_string(h) for h in job.get("highlights", []) if safe_string(h)]
            }
            start_date = convert_date(job.get("startDate"))
            if start_date is not None:
                entry["start_date"] = start_date
            else:
                print(f"Debug: start_date omitido para entrada de trabajo de {company}: '{job.get('startDate')}'")
            end_date = convert_date(job.get("endDate"))
            if end_date is not None:
                entry["end_date"] = end_date
            else:
                print(f"Debug: end_date omitido para entrada de trabajo de {company}: '{job.get('endDate')}'")
            sections["Experience"].append(entry)

    education = adapted_cv.get("education", [])
    if education:
        sections["Education"] = []
        print("Debug: Fechas y grados de educación:")
        for edu in education:
            if not isinstance(edu, dict):
                print(f"Debug: Entrada de educación '{edu}' descartada: no es un diccionario")
                continue
            print(f"Debug: Institución: {edu.get('institution')}, studyType: {edu.get('studyType')}, startDate: {edu.get('startDate')}, endDate: {edu.get('endDate')}")
        for edu in education:
            if not isinstance(edu, dict):
                continue
            institution = safe_string(edu.get("institution"), "Unknown")
            entry = {
                "institution": institution,
                "area": safe_string(edu.get("studyType")),
                "degree": get_degree_abbreviation(edu.get("studyType")),
                "location": safe_string(edu.get("location")),
                "highlights": [safe_string(h) for h in edu.get("courses", []) if safe_string(h)]
            }
            start_date = convert_date(edu.get("startDate"))
            if start_date is not None:
                entry["start_date"] = start_date
            else:
                print(f"Debug: start_date omitido para entrada de educación de {institution}: '{edu.get('startDate')}'")
            end_date = convert_date(edu.get("endDate"))
            if end_date is not None:
                entry["end_date"] = end_date
            else:
                print(f"Debug: end_date omitido para entrada de educación de {institution}: '{edu.get('endDate')}'")
            sections["Education"].append(entry)

    skills = adapted_cv.get("skills", [])
    if skills:
        skill_list = []
        for skill in skills:
            if not isinstance(skill, dict):
                print(f"Debug: Habilidad '{skill}' descartada: no es un diccionario")
                continue
            name = safe_string(skill.get("name"))
            if name:
                skill_list.append(name)
            else:
                print(f"Debug: Habilidad '{name}' descartada: nombre vacío")
        if skill_list:
            sections["Skills"] = [
                {
                    "label": "Skills",
                    "details": ", ".join(skill_list)
                }
            ]
        else:
            print(f"Debug: No se incluyeron habilidades válidas en YAML")

    projects = adapted_cv.get("projects", [])
    if projects:
        sections["Projects"] = []
        for proj in projects:
            if not isinstance(proj, dict):
                print(f"Debug: Proyecto '{proj}' descartado: no es un diccionario")
                continue
            name = safe_string(proj.get("name"), "Unnamed Project")
            start_date = convert_date(proj.get("startDate"))
            end_date = convert_date(proj.get("endDate"))
            date_range = ""
            if start_date and end_date:
                date_range = f"{start_date} - {end_date}"
            elif start_date:
                date_range = f"{start_date}"
            elif end_date:
                date_range = f"{end_date}"
            if not start_date:
                print(f"Debug: start_date omitido para proyecto {name}: '{proj.get('startDate')}'")
            if not end_date:
                print(f"Debug: end_date omitido para proyecto {name}: '{proj.get('endDate')}'")
            sections["Projects"].append(
                (
                    f"{name}" +
                    (f" ({date_range})" if date_range else "") +
                    f": {safe_string(proj.get('description'))}\n" +
                    "\n".join(f"- {safe_string(h)}" for h in proj.get("highlights", []) if safe_string(h))
                ).strip()
            )

    languages = adapted_cv.get("languages", [])
    if languages:
        language_list = []
        for lang in languages:
            if not isinstance(lang, dict):
                print(f"Debug: Idioma '{lang}' descartado: no es un diccionario")
                continue
            language = safe_string(lang.get("language"))
            if not language:
                print(f"Debug: Idioma '{language}' descartado: nombre vacío")
                continue
            fluency = safe_string(lang.get("fluency"))
            language_entry = f"{language} ({fluency})" if fluency else language
            language_list.append(language_entry)
        if language_list:
            sections["Languages"] = [
                {
                    "label": "Languages",
                    "details": ", ".join(language_list)
                }
            ]
        else:
            print(f"Debug: No se incluyeron idiomas válidos en YAML")

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "cv_rendercv.yaml")
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(rendercv_data, f, allow_unicode=True, sort_keys=False)

    return output_file





















def generate_rendercv_pdf(yaml_path: str, output_dir: str = "rendercv_output", final_pdf_name: str = "final_cv.pdf") -> str:
    """
    Generates a PDF from a RenderCV YAML file using the RenderCV CLI.

    Args:
        yaml_path (str): Path to the RenderCV YAML file.
        output_dir (str): Directory where RenderCV saves the PDF.
        final_pdf_name (str): Name of the final PDF file to copy to.

    Returns:
        str: Path to the final PDF file.

    Raises:
        FileNotFoundError: If no PDF is generated or YAML file is missing.
        subprocess.CalledProcessError: If RenderCV CLI fails.
    """
    # Ensure YAML file exists
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"YAML file not found at: {yaml_path}")

    # Run RenderCV CLI to generate PDF
    try:
        subprocess.run(
            ["rendercv", "render", yaml_path],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        st.error(f"RenderCV failed with exit code {e.returncode}")
        st.write(f"STDOUT:\n{e.stdout}")
        st.write(f"STDERR:\n{e.stderr}")
        raise
    except FileNotFoundError:
        st.error("RenderCV CLI not found. Ensure 'rendercv' is installed and in your PATH.")
        raise

    # Find generated PDF
    pdf_files = glob.glob(os.path.join(output_dir, "*.pdf"))
    if not pdf_files:
        st.error(f"No PDF generated in {output_dir}")
        raise FileNotFoundError(f"No PDF generated in {output_dir}")
    
    # Get the most recent PDF
    latest_pdf = max(pdf_files, key=os.path.getmtime)

    # Copy to final_pdf_name
    final_pdf_path = os.path.join(os.getcwd(), final_pdf_name)
    shutil.copy(latest_pdf, final_pdf_path)

    return final_pdf_path









































































































def calculate_total_experience(work_history: list) -> float:
    """Calcula los años totales de experiencia laboral desde el historial de trabajo."""
    total_months = 0
    current_year = datetime.now().year
    current_month = datetime.now().month

    for job in work_history:
        start_date = job.get("startDate", "")
        end_date = job.get("endDate", "present")

        if not start_date:
            continue

        try:
            start_month, start_year = start_date.split()
            start_month = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
                           "Jul": 7, "Ago": 8, "Sept": 9, "Oct": 10, "Nov": 11, "Dic": 12}[start_month]
            start_year = int(start_year)
        except (ValueError, KeyError):
            continue

        if end_date.lower() == "present":
            end_month, end_year = current_month, current_year
        else:
            try:
                end_month, end_year = end_date.split()
                end_month = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
                             "Jul": 7, "Ago": 8, "Sept": 9, "Oct": 10, "Nov": 11, "Dic": 12}[end_month]
                end_year = int(end_year)
            except (ValueError, KeyError):
                continue

        months = (end_year - start_year) * 12 + (end_month - start_month)
        if months > 0:
            total_months += months

    return total_months / 12

def normalize_text(text: str) -> str:
    """Normaliza texto eliminando espacios, mayúsculas y caracteres especiales."""
    # Convertir a minúsculas y eliminar espacios y signos de puntuación
    text = text.lower()
    text = re.sub(r'[\s$$      $$,.;:-]+', '', text)
    return text

def calculate_ats_score_old(cv_data: dict, job_data: dict, cv_work_history: list = None) -> dict:
    """
    Calcula el puntaje ATS comparando CV y oferta laboral de forma robusta.
    - Normaliza texto para ignorar espacios, mayúsculas y signos.
    - Incluye experiencia del CV aunque la oferta no la tenga.
    - Diseñado para ser genérico y resistente a variaciones.
    """
    # Normalizar habilidades, palabras clave e idiomas
    cv_skills_raw = cv_data.get("skills", [])
    cv_keywords_raw = cv_data.get("keywords", [])
    cv_languages_raw = cv_data.get("languages", [])

    job_skills_raw = job_data.get("skills", [])
    job_keywords_raw = job_data.get("keywords", [])
    job_languages_raw = job_data.get("languages", [])

    # Normalizar listas completas
    cv_skills = set(normalize_text(skill) for skill in cv_skills_raw)
    cv_keywords = set(normalize_text(keyword) for keyword in cv_keywords_raw)
    cv_languages = set(normalize_text(lang) for lang in cv_languages_raw)

    job_skills = set(normalize_text(skill) for skill in job_skills_raw)
    job_keywords = set(normalize_text(keyword) for keyword in job_keywords_raw)
    job_languages = set(normalize_text(lang) for lang in job_languages_raw)

    # Calcular coincidencias
    skill_matches = len(cv_skills & job_skills)
    keyword_matches = len(cv_keywords & job_keywords)
    language_matches = len(cv_languages & job_languages)

    # Calcular experiencia del CV si se proporciona work_history
    resume_years = calculate_total_experience(cv_work_history) if cv_work_history else 0

    # Calcular puntaje ATS
    score = 0
    max_score = 100

    # Skills (40%): Más peso porque es crítico
    skill_score = (skill_matches / max(len(job_skills), 1)) * 40 if job_skills else 40
    score += skill_score

    # Keywords (30%)
    keyword_score = (keyword_matches / max(len(job_keywords), 1)) * 30 if job_keywords else 30
    score += keyword_score

    # Languages (10%)
    language_score = (language_matches / max(len(job_languages), 1)) * 10 if job_languages else 10
    score += language_score

    # Experience (20%): Solo basado en CV, con un máximo relativo
    # Asumimos que 5 años es un "máximo razonable" para escalar si la oferta no lo especifica
    exp_score = min(resume_years / 5, 1) * 20 if resume_years > 0 else 0
    score += exp_score

    # Detalles para retroalimentación
    missing_skills = list(job_skills - cv_skills)
    missing_keywords = list(job_keywords - cv_keywords)
    missing_languages = list(job_languages - cv_languages)

    return {
        "score": min(round(score, 2), max_score),
        "missing_skills": missing_skills,
        "missing_keywords": missing_keywords,
        "missing_languages": missing_languages,
        "skill_matches": skill_matches,
        "total_skills": len(job_skills),
        "keyword_matches": keyword_matches,
        "total_keywords": len(job_keywords),
        "language_matches": language_matches,
        "total_languages": len(job_languages),
        "resume_years": resume_years
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
