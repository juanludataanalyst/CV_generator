import os
import json
import asyncio
from dotenv import load_dotenv
from typing import Dict, Any
from src.models import JsonResume
from pipeline import run_llm


def parse_to_json_resume_sync(text: str) -> Dict:
    """
    Parses CV text into JSON Resume format using an LLM via OpenRouter with pydantic-ai.

    Args:
        text (str): Extracted text from the CV.

    Returns:
        Dict: JSON Resume formatted data.
    """
   
   
    prompt = f"""
You are an expert in CV parsing.

Take the following extracted CV text, which may have mixed sections (e.g., Profile and Experience blended due to layout issues), and structure it into the JSON Resume standard format.

Separate clearly the "Profile" (summary) from "Professional Experience" (work history with dates and descriptions) and other sections like Education, Skills, Languages, and Projects.

Preserve the original content without adding or modifying information beyond structuring.

Here is the JSON Resume schema for reference:
- basics: {{name, label, email, phone, url, summary, profiles: [{{network, username, url}}]}}
- work: [{{company, position, website, startDate, endDate, summary, highlights}}]
- education: [{{institution, area, studyType, startDate, endDate, score, courses}}]
- skills: [{{name, level, keywords}}]
- languages: [{{language, fluency}}]
- projects: [{{name, description, highlights, keywords, startDate, endDate, url, roles, entity, type}}]

CV Text:
\"\"\"
{text}
\"\"\"

Return the result as a JSON object. Use full URLs (e.g., "https://github.com/username") and set fields to null if no data is present instead of empty strings.
"""

  
    result = run_llm( prompt)
    print("LLM response (cv_parser):")
    print(result.data)
    json_str = result.data

    # Ocultar salida cruda del LLM
    try:
        json_cv = json.loads(json_str)
    except json.JSONDecodeError:
        # Sometimes LLMs return JSON with trailing commas or formatting issues
        # You may want to clean or fix common issues here
        raise ValueError("Failed to parse LLM output as JSON")

    def preprocess_json(data):
        """
        Recursively clean JSON:
        - Convert empty string URLs to None
        - Convert relative URLs to absolute URLs
        """
        if isinstance(data, dict):
            new_data = {}
            for k, v in data.items():
                if isinstance(v, str):
                    if k in ("url", "website") and (v.strip() == "" or v.strip() is None):
                        new_data[k] = None
                    elif k in ("url", "website") and not v.startswith("http"):
                        new_data[k] = "https://" + v.lstrip("/")
                    else:
                        new_data[k] = v
                elif isinstance(v, (dict, list)):
                    new_data[k] = preprocess_json(v)
                else:
                    new_data[k] = v
            return new_data
        elif isinstance(data, list):
            return [preprocess_json(item) for item in data]
        else:
            return data

    json_cv = preprocess_json(json_cv)

    # Reemplazar None o "" en campos string opcionales por ""
    # En campos URL por None
    # En campos lista por []
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



