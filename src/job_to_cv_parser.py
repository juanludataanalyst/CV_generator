import os
import json
import asyncio
import re
from dotenv import load_dotenv
from typing import Dict
from dateutil import parser
from datetime import datetime

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
    Extrae habilidades, experiencia y palabras clave de una descripción de trabajo o CV usando un LLM.
    """
    print("Extrayendo datos estructurados del " + ("job description" if is_job else "CV") + "...")
    if is_job:
        prompt = f"""
Extrae la siguiente información de esta descripción de trabajo:
1. Una lista de TODAS las habilidades requeridas (por ejemplo, "Python", "Machine Learning").
2. Los años mínimos de experiencia requeridos (como número, por ejemplo, 3). Si no se especifica, devuelve 0.
3. Las 10 palabras clave o frases más importantes que deberían aparecer en un CV para coincidir con este trabajo (por ejemplo, "data analysis", "cloud computing").

Texto:
\"\"\"
{text}
\"\"\"

Devuelve el resultado como un objeto JSON con las claves: "skills", "experience", "keywords".
Responde SÓLO con el objeto JSON.
"""
    else:
        prompt = f"""
Extrae la siguiente información de este CV:
1. Una lista de TODAS las habilidades mencionadas.
2. Las 10 palabras clave o frases más importantes que representen la experiencia del candidato.

Texto:
\"\"\"
{text}
\"\"\"

Devuelve el resultado como un objeto JSON con las claves: "skills", "keywords".
Responde SÓLO con el objeto JSON.
"""
    result = await agent.run(prompt)
    print("Datos estructurados extraídos con éxito.")
    return json.loads(result.data)

def calculate_total_experience(cv_json: dict) -> int:
    """
    Calcula los años totales de experiencia desde la sección "work" del CV JSON.
    """
    work_entries = cv_json.get("work", [])
    if not work_entries:
        return 0

    earliest_start = None
    latest_end = None

    for entry in work_entries:
        start_str = entry.get("startDate")
        end_str = entry.get("endDate", "")  # Si endDate está vacío, es un trabajo actual

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
            # Trabajo actual, usa la fecha de hoy
            latest_end = datetime.now()

    if earliest_start and latest_end:
        total_years = (latest_end - earliest_start).days / 365.25
        return int(total_years)
    return 0

def calculate_ats_score(job_data: Dict, resume_data: Dict, resume_text: str, cv_json: dict) -> Dict:
    """
    Calcula el puntaje de compatibilidad ATS basado en habilidades, experiencia y palabras clave.
    """
    score = 0
    max_score = 100

    # Habilidades (40%)
    job_skills = set(s.lower() for s in job_data['skills'])
    resume_skills = set(s.lower() for s in resume_data['skills'])
    skill_matches = len(job_skills.intersection(resume_skills))
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

async def adapt_cv_to_job_async(cv_json: dict, job_description: str) -> dict:
    """
    Adapta un CV JSON a una descripción de trabajo, optimizando al máximo éticamente alcanzable.
    Muestra logs en tiempo real al usuario.
    """
    print("Iniciando proceso de optimización del CV...")
    cv_text = json.dumps(cv_json, indent=2)

    # Extraer datos estructurados del job description
    job_data = await extract_structured_data(job_description, is_job=True)
    print("Analizando compatibilidad inicial del CV con la oferta...")
    resume_data = await extract_structured_data(cv_text, is_job=False)

    # Calcular puntaje ATS inicial
    initial_match = calculate_ats_score(job_data, resume_data, cv_text, cv_json)
    initial_score = initial_match['score']

    print("\n=== Análisis ATS Inicial ===")
    print(f"Puntaje ATS Inicial: {initial_score}%")
    print(f"Habilidades Coincidentes: {initial_match['skill_matches']} / {initial_match['total_skills']}")
    print(f"Palabras Clave Coincidentes: {initial_match['keyword_matches']} / {initial_match['total_keywords']}")
    print(f"Experiencia: {initial_match['resume_years']} años (Trabajo requiere: {initial_match['job_years']})")
    print(f"Habilidades Faltantes: {initial_match['missing_skills']}")
    print(f"Palabras Clave Faltantes: {initial_match['missing_keywords']}")
    print(f"Brecha de Experiencia: {initial_match['experience_gap']} años")

    # Si el puntaje inicial es menor a 75%, proceder con optimización
    if initial_score < 75:
        print("\nOptimizando el CV para alcanzar el máximo puntaje ético posible...")
        prompt = f"""
Eres un experto en redacción de CVs y optimización ATS.

Tu objetivo es optimizar el CV para alcanzar el máximo porcentaje de compatibilidad ético posible con el sistema ATS de la empresa para la descripción de trabajo proporcionada.

Instrucciones:
- Analiza las habilidades, experiencia y palabras clave del CV y compáralas con la descripción del trabajo.
- Resalta y enfatiza las fortalezas existentes del candidato que coincidan con los requisitos.
- Incorpora habilidades y palabras clave faltantes de la descripción del trabajo solo si son plausibles según el perfil del candidato o si son razonablemente aprendibles, distribuyéndolas naturalmente en las secciones (por ejemplo, resumen, experiencia laboral, habilidades).
- No inventes información falsa.
- Preserva todas las entradas de experiencia laboral con sus fechas originales de inicio y fin.
- Mantén el formato JSON Resume y un tono profesional y natural.

Detalles de compatibilidad inicial:
- Habilidades faltantes: {', '.join(initial_match['missing_skills']) or 'Ninguna'}
- Palabras clave faltantes: {', '.join(initial_match['missing_keywords']) or 'Ninguna'}
- Brecha de experiencia: {initial_match['experience_gap']} años

Descripción del Trabajo:
\"\"\"
{job_description}
\"\"\"

CV JSON:
\"\"\"
{cv_text}
\"\"\"

Devuelve el CV actualizado como un objeto JSON.
Responde SÓLO con el CV actualizado como un objeto JSON válido.
"""
        result = await agent.run(prompt)
        updated_cv = json.loads(result.data)
    else:
        print("\nEl puntaje ATS inicial ya es suficientemente alto (>=75%). No se requiere optimización.")
        updated_cv = cv_json

    # Recalcular puntaje ATS final
    print("Calculando el puntaje ATS final del CV optimizado...")
    updated_cv_text = json.dumps(updated_cv, indent=2)
    updated_resume_data = await extract_structured_data(updated_cv_text, is_job=False)
    final_match = calculate_ats_score(job_data, updated_resume_data, updated_cv_text, updated_cv)
    updated_cv["ats_match_score"] = final_match["score"]

    print("\n=== Análisis ATS Final ===")
    print(f"Puntaje ATS Final (Máximo Éticamente Alcanzable): {final_match['score']}%")
    print(f"Habilidades Coincidentes: {final_match['skill_matches']} / {final_match['total_skills']}")
    print(f"Palabras Clave Coincidentes: {final_match['keyword_matches']} / {final_match['total_keywords']}")
    print(f"Experiencia: {final_match['resume_years']} años (Trabajo requiere: {final_match['job_years']})")
    print("Proceso de optimización completado.")

    return updated_cv

def adapt_cv_to_job(cv_json: dict, job_description: str) -> dict:
    """
    Envoltorio síncrono para la adaptación asíncrona del CV.
    """
    return asyncio.run(adapt_cv_to_job_async(cv_json, job_description))

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