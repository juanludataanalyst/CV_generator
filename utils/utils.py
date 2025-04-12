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
    Extracts all text from a job posting URL and uses an LLM agent to clean and extract the job description.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

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
            else:
                break  # Salir del bucle si hay resultado válido

        return result.strip() if result else "ERROR: LLM failed to return a valid response"

    except requests.RequestException as e:
        return f"Error extracting content: {str(e)}"

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
        Extracts skills, experience, keywords and language from a job description using an LLM.
        """
        print("Extracting structured data from " + ("job description" if is_job else "CV") + "...")
        if is_job:
            prompt = f"""
        Extract the following information from this job description and return it as a JSON object:
        1. A list of ALL required skills (e.g., "Python", "Machine Learning").
        2. The minimum years of experience required (as a number, e.g., 3). If not specified, return 0.
        3. The most important keywords or phrases that should appear in a resume to match this job (e.g., "data analysis", "cloud computing","python").

        Text:
        \"\"\"
        {text}
        \"\"\"

        Return the result as a JSON object with keys: "skills", "experience", "keywords" and "languages"
        Respond ONLY with the JSON object.
        """
        else:
            prompt = f"""
          Extract the following information from this CV and return it as a JSON object:
        1. A list of ALL skills (e.g., "Python", "Machine Learning").
        2. The most important keywords or phrases that should appear in a resume to match this job (e.g., "data analysis", "cloud computing","python").

        Text:
        \"\"\"
        {text}
        \"\"\"

        Return the result as a JSON object with keys: "skills", "experience", "keywords" and "languages"
        Respond ONLY with the JSON object.


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

          if is_job:
             open("file_outputs/job_summary_llm_output.txt", 'w', encoding='utf-8').write(result)
          else:
             open("file_outputs/cv_summary_llm_output.txt", 'w', encoding='utf-8').write(result)

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

def parse_to_json_resume_sync(text: str) -> Dict:
    """
    Parses CV text into JSON Resume format using an LLM via OpenRouter with pydantic-ai.
    """
    prompt = f"""
    You are an expert in CV parsing.

    Take the following extracted CV text, which may have mixed sections (e.g., Profile and Experience blended due to layout issues), and structure it into the JSON Resume standard format.

    Separate clearly the "Profile" (summary) from "Professional Experience" (work history with dates and descriptions) and other sections like Education, Skills, Languages, and Projects.

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

def match_with_llm(cv_items: list, job_items: list, item_type: str) -> dict:
    """
    Uses an LLM to match skills, keywords, or languages between CV and job offer.
    
    Args:
        cv_items (list): List of items from the CV (skills, keywords, or languages).
        job_items (list): List of items from the job offer (skills, keywords, or languages).
        item_type (str): Type of items ('skills', 'keywords', or 'languages').
    
    Returns:
        dict: JSON with matches and missing items.
    """
    prompt = (
        f"You are an expert in job skills analysis. I have two lists of {item_type}:\n\n"
        f"{item_type.capitalize()} from CV: {cv_items}\n"
        f"{item_type.capitalize()} from job offer: {job_items}\n\n"
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

def calculate_ats_score(skills_match: dict, keywords_match: dict, languages_match: dict, total_job_skills: int, total_job_keywords: int, total_job_languages: int) -> float:
    """
    Calculate the ATS score based on matches for skills, keywords, and languages.

    - Keywords: 65% weight
    - Skills: 35% weight
    - Languages: Required condition (if any required language is missing, score is 0)

    Args:
        skills_match (dict): Dictionary with 'matches' and 'missing' for skills.
        keywords_match (dict): Dictionary with 'matches' and 'missing' for keywords.
        languages_match (dict): Dictionary with 'matches' and 'missing' for languages.
        total_job_skills (int): Total number of skills required in the job offer.
        total_job_keywords (int): Total number of keywords required in the job offer.
        total_job_languages (int): Total number of languages required in the job offer.

    Returns:
        float: ATS score as a percentage (0-100).
    """
    # Check if any required language is missing
    missing_languages = languages_match.get('missing', [])
    if missing_languages:
        return 0.0

    # Count matches
    skill_matches = len(skills_match.get('matches', []))
    keyword_matches = len(keywords_match.get('matches', []))

    # Calculate match percentages
    skills_percentage = (skill_matches / total_job_skills) if total_job_skills > 0 else 0
    keywords_percentage = (keyword_matches / total_job_keywords) if total_job_keywords > 0 else 0

    # Apply weights: 65% keywords, 35% skills
    score = (0.65 * keywords_percentage) + (0.35 * skills_percentage)

    # Return score as percentage
    return round(score * 100, 2)


def adapt_cv_with_llm(original_cv: dict, job_data: dict, skills_match: dict, keywords_match: dict) -> dict:
    """
    Adapts the original CV to improve ATS score by incorporating matched and inferred skills/keywords.

    Args:
        original_cv (dict): Original CV in JSON Resume format.
        job_data (dict): Job offer data with skills, keywords, and languages.
        skills_match (dict): Dictionary with 'matches' and 'missing' for skills.
        keywords_match (dict): Dictionary with 'matches' and 'missing' for keywords.

    Returns:
        dict: Adapted CV in JSON Resume format, validated with Pydantic.
    """
    # Depuración: Imprimir los argumentos para verificar su estructura
    print("Debugging adapt_cv_with_llm inputs:")
    print("original_cv:", json.dumps(original_cv, indent=2))
    print("job_data:", json.dumps(job_data, indent=2))
    print("skills_match:", json.dumps(skills_match, indent=2))
    print("keywords_match:", json.dumps(keywords_match, indent=2))

    # Validar que los argumentos tengan la estructura esperada
    if not isinstance(original_cv, dict):
        raise ValueError("original_cv must be a dictionary")
    if not isinstance(job_data, dict):
        raise ValueError("job_data must be a dictionary")
    if not isinstance(skills_match, dict) or 'matches' not in skills_match or 'missing' not in skills_match:
        raise ValueError("skills_match must be a dictionary with 'matches' and 'missing' keys")
    if not isinstance(keywords_match, dict) or 'matches' not in keywords_match or 'missing' not in keywords_match:
        raise ValueError("keywords_match must be a dictionary with 'matches' and 'missing' keys")

    # Asegurarnos de que las listas contengan solo strings
    job_skills = [str(item) for item in job_data.get('skills', [])]
    job_keywords = [str(item) for item in job_data.get('keywords', [])]
    job_languages = [str(item) for item in job_data.get('languages', [])]
    matched_skills = [str(item) for item in skills_match.get('matches', [])]
    missing_skills = [str(item) for item in skills_match.get('missing', [])]
    matched_keywords = [str(item) for item in keywords_match.get('matches', [])]
    missing_keywords = [str(item) for item in keywords_match.get('missing', [])]

    # Construir el prompt con formateo seguro
    prompt = f'''
    You are an expert in CV optimization for ATS systems. I have an original CV and a job offer:

    Original CV (JSON Resume format):
    {json.dumps(original_cv, indent=2)}

    Job Offer:
    - Skills required: {json.dumps(job_skills)}
    - Keywords: {json.dumps(job_keywords)}
    - Languages: {json.dumps(job_languages)}

    Matches:
    - Skills matched: {json.dumps(matched_skills)}
    - Keywords matched: {json.dumps(matched_keywords)}

    Missing:
    - Skills missing: {json.dumps(missing_skills)}
    - Keywords missing: {json.dumps(missing_keywords)}

    Your task is:
    1. Adapt the CV to improve its ATS score by:
    - Highlighting matched skills and keywords in the summary, work highlights, and skills section.
    - Inferring skills or keywords from the CV that align with missing ones, if they can be reasonably derived (e.g., "Python" and "pandas" imply "data analysis").
    - Reorganizing content to prioritize job-relevant information.
    2. Do NOT invent skills, experiences, or qualifications not supported by the original CV.
    3. Return the adapted CV in the same JSON Resume format, ensuring all fields are valid.

    Rules:
    - Be ethical: only include changes backed by the original CV.
    - Prioritize clarity and relevance for ATS systems.
    - Maintain the structure of the JSON Resume schema.
    - If a skill or keyword cannot be inferred, do not include it.
    - Use a low temperature (0.2) for consistency.

    Example:
    If the CV has "Python" and the job requires "data analysis", you might update:
    - Summary: Add "Experienced in data analysis using Python."
    - Skills: Add {{"name": "Data Analysis", "level": null, "keywords": []}}.
    - Work highlights: Add "Performed data analysis with Python to support decisions."

    Output:
    Return the full adapted CV as a JSON object, enclosed in ```json``` markers.
    ```json
    {{"basics": {{"name": "Example", ...}}, ...}}
    '''



    print("Estamos dentro de la funcion:")
    print(original_cv)
    print(type(original_cv))
    print(job_data)
    print(type(job_data))
    print(skills_match)
    print(type(skills_match))
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
