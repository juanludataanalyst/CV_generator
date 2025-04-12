import streamlit as st
import os
import json
import glob
import shutil
import subprocess
from utils.utils import (
    extract_cv_text,
    parse_to_json_resume_sync,
    scrape_job_description,
    adapt_cv_to_job,
    extract_job_description_data,
    match_with_llm,
    calculate_ats_score_old,
    calculate_ats_score,
    adapt_cv_with_llm
)

st.title("CV Adapter - ATS Optimizer")

# Inicializar estados en session_state
if "uploaded_cv_path" not in st.session_state:
    st.session_state["uploaded_cv_path"] = None
if "scraping_failed" not in st.session_state:
    st.session_state["scraping_failed"] = False
if "continue_with_manual" not in st.session_state:
    st.session_state["continue_with_manual"] = False
if "manual_job_text" not in st.session_state:
    st.session_state["manual_job_text"] = ""

# Subida del CV
uploaded_file = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
if uploaded_file and not st.session_state["uploaded_cv_path"]:
    with open("uploaded_cv.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.session_state["uploaded_cv_path"] = "uploaded_cv.pdf"

# Input de la URL
job_url = st.text_input("Paste the job description URL")

log_area = st.empty()
logs = []

def log(msg):
    logs.append(msg)
    log_area.text("\n".join(logs[-20:]))

# Botón para iniciar el proceso
if (st.button("Generate ATS-optimized CV") 
    and st.session_state["uploaded_cv_path"] 
    and job_url 
    and not st.session_state["scraping_failed"] 
    and not st.session_state["continue_with_manual"]):
    with st.spinner("Processing..."):
        log("Starting pipeline...")
        try:
            os.makedirs("file_outputs", exist_ok=True)

            # Extraer y guardar la descripción del trabajo
            job_description = scrape_job_description(job_url)
            st.success("Job description scraped successfully.")
            with open("file_outputs/job_description.txt", 'w', encoding='utf-8') as f:
                f.write(job_description)

            # Extraer datos de la oferta laboral
            job_data = extract_job_description_data(job_description, is_job=True)
            st.success("Job description data extracted successfully.")
            with open("file_outputs/job_description_data.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(job_data, ensure_ascii=False))

            # Extraer y guardar el texto del CV
            extracted_text = extract_cv_text(st.session_state["uploaded_cv_path"])
            with open("file_outputs/extracted_cv_text.txt", 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            st.success("CV text extracted successfully.")

            # Parsear el CV a JSON
            parsed_cv = parse_to_json_resume_sync(extracted_text)
            st.success("CV parsed successfully.")
            with open("file_outputs/resume.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(parsed_cv, ensure_ascii=False))

            cv_data = extract_job_description_data(extracted_text, is_job=False)
            st.success("CV data extracted successfully.")

            keywords_match = match_with_llm(cv_data.get('keywords', []), job_data.get('keywords', []), 'keywords')

            # Imprimir resultados de palabras clave en un formato bonito
            st.subheader("Keywords Matching")
            st.write(", ".join(job_data.get('keywords', [])))
            st.write("**Matched Keywords:**")
            matched_keywords = keywords_match.get('matches', [])
            st.write(", ".join(matched_keywords) if matched_keywords else "Ninguna coincidencia")
            st.write("**Missing Keywords:**")
            missing_keywords = keywords_match.get('missing', [])
            st.write(", ".join(missing_keywords) if missing_keywords else "Ninguna faltante")
            st.write(f"**Total Keywords Matches:** {len(matched_keywords)} de {len(job_data.get('keywords', []))}")

            # Probar el matcheo con LLM e imprimir resultados
            skills_match = match_with_llm(cv_data.get('skills', []), job_data.get('skills', []), 'skills')

            # Imprimir resultados de habilidades en un formato bonito
            st.subheader("Skills Matching")
            st.write("**Matched Skills:**")
            matched_skills = skills_match.get('matches', [])
            st.write(", ".join(matched_skills) if matched_skills else "Ninguna coincidencia")
            st.write("**Missing Skills:**")
            missing_skills = skills_match.get('missing', [])
            st.write(", ".join(missing_skills) if missing_skills else "Ninguna faltante")
            st.write(f"**Total Skills Matches:** {len(matched_skills)} de {len(job_data.get('skills', []))}")

            languages_match = match_with_llm(cv_data.get('languages', []), job_data.get('languages', []), 'languages')

            # Imprimir resultados de idiomas en un formato bonito
            st.subheader("Languages Matching")
            st.write("**Matching Languages:**")
            matched_languages = languages_match.get('matches', [])
            st.write(", ".join(matched_languages) if matched_languages else "Ninguna coincidencia")
            st.write("**Missing Languages:**")
            missing_languages = languages_match.get('missing', [])
            st.write(", ".join(missing_languages) if missing_languages else "Ninguna faltante")
            st.write(f"**Total Languages Matches:** {len(matched_languages)} de {len(job_data.get('languages', []))}")

            st.success("ATS score calculated")

            skills_job = job_data.get('skills', [])
            keywords_job = job_data.get('keywords', [])
            languages_job = job_data.get('languages', [])

            skills_job_count = len(skills_job) if skills_job else 0
            keywords_job_count = len(keywords_job) if keywords_job else 0
            languages_job_count = len(languages_job) if languages_job else 0

            score = calculate_ats_score(skills_match, keywords_match, languages_match, skills_job_count, keywords_job_count, languages_job_count)

            st.write(f"**ATS Score (Original CV):** {score}%")

            adapted_cv = adapt_cv_with_llm(parsed_cv, job_data, skills_match, keywords_match)

            # Mostrar CV adaptado
            st.subheader("CV Adaptado")
            st.json(adapted_cv)

            # Calcular ATS score para el CV adaptado
            st.subheader("ATS Score del CV Adaptado")
            # Extraer habilidades, palabras clave e idiomas del CV adaptado
            adapted_skills = [skill["name"] for skill in adapted_cv.get("skills", [])]
            # Para palabras clave, usaremos las del summary y highlights
            adapted_keywords = []
            if adapted_cv.get("basics", {}).get("summary"):
                adapted_keywords.extend(adapted_cv["basics"]["summary"].split())
            for work in adapted_cv.get("work", []):
                adapted_keywords.extend([word for hl in work.get("highlights", []) for word in hl.split()])
            adapted_keywords = list(set(adapted_keywords))  # Eliminar duplicados
            adapted_languages = [lang["language"] for lang in adapted_cv.get("languages", [])]

            # Comparar con la oferta laboral
            adapted_skills_match = match_with_llm(adapted_skills, job_data.get('skills', []), 'skills')
            adapted_keywords_match = match_with_llm(adapted_keywords, job_data.get('keywords', []), 'keywords')
            adapted_languages_match = match_with_llm(adapted_languages, job_data.get('languages', []), 'languages')

            # Calcular el nuevo ATS score
            adapted_score = calculate_ats_score(
                adapted_skills_match,
                adapted_keywords_match,
                adapted_languages_match,
                skills_job_count,
                keywords_job_count,
                languages_job_count
            )

            # Mostrar el nuevo score y detalles
            st.write(f"**ATS Score (Adapted CV):** {adapted_score}%")
            st.metric("Mejora en ATS Score", f"{adapted_score - score:.2f}%", delta_color="normal")
            
            st.write("**Matched Skills (Adapted CV):**")
            adapted_matched_skills = adapted_skills_match.get('matches', [])
            st.write(", ".join(adapted_matched_skills) if adapted_matched_skills else "Ninguna coincidencia")
            st.write("**Missing Skills (Adapted CV):**")
            adapted_missing_skills = adapted_skills_match.get('missing', [])
            st.write(", ".join(adapted_missing_skills) if adapted_missing_skills else "Ninguna faltante")
            st.write(f"**Total Skills Matches (Adapted CV):** {len(adapted_matched_skills)} de {len(job_data.get('skills', []))}")

            st.write("**Matched Keywords (Adapted CV):**")
            adapted_matched_keywords = adapted_keywords_match.get('matches', [])
            st.write(", ".join(adapted_matched_keywords) if adapted_matched_keywords else "Ninguna coincidencia")
            st.write("**Missing Keywords (Adapted CV):**")
            adapted_missing_keywords = adapted_keywords_match.get('missing', [])
            st.write(", ".join(adapted_missing_keywords) if adapted_missing_keywords else "Ninguna faltante")
            st.write(f"**Total Keywords Matches (Adapted CV):** {len(adapted_matched_keywords)} de {len(job_data.get('keywords', []))}")

            st.write("**Matched Languages (Adapted CV):**")
            adapted_matched_languages = adapted_languages_match.get('matches', [])
            st.write(", ".join(adapted_matched_languages) if adapted_matched_languages else "Ninguna coincidencia")
            st.write("**Missing Languages (Adapted CV):**")
            adapted_missing_languages = adapted_languages_match.get('missing', [])
            st.write(", ".join(adapted_missing_languages) if adapted_missing_languages else "Ninguna faltante")
            st.write(f"**Total Languages Matches (Adapted CV):** {len(adapted_matched_languages)} de {len(job_data.get('languages', []))}")

            # Calcular el puntaje ATS usando el CV parseado y los datos de la oferta
            ats_result = calculate_ats_score_old(cv_data, job_data)
            st.success("ATS score calculated successfully.")
            
            # UI mejorada
            st.subheader("Resultados del análisis ATS")
            st.metric("Puntaje ATS (Antiguo)", f"{ats_result['score']}%", delta=None)

            # Pestañas para organizar la información
            tab1, tab2, tab3 = st.tabs(["Oferta laboral", "Tu CV", "Análisis ATS"])

            with tab1:
                st.write("**Habilidades requeridas:**")
                st.write(", ".join(job_data.get("skills", [])))
                st.write("**Palabras clave:**")
                st.write(", ".join(job_data.get("keywords", [])))
                st.write("**Experiencia mínima:**")
                st.write(f"{job_data.get('experience', 0)} años")
                st.write("**Idiomas:**")
                st.write(", ".join(job_data.get("languages", [])))

            with tab2:
                st.write("**Habilidades en tu CV:**")
                st.write(", ".join(cv_data.get("skills", [])))
                st.write("**Palabras clave:**")
                st.write(", ".join(cv_data.get("keywords", [])))
                st.write("**Experiencia estimada:**")
                st.write(f"{ats_result['resume_years']:.2f} años")
                st.write("**Idiomas:**")
                st.write(", ".join(cv_data.get("languages", [])))

            with tab3:
                st.write("**Coincidencias de habilidades:**")
                matched_skills = [s for s in job_data["skills"] if s.lower() in [sk.lower() for sk in cv_data["skills"]]]
                st.write(f"{ats_result['skill_matches']} de {ats_result['total_skills']}")
                st.write(", ".join(matched_skills))
                st.write("**Habilidades faltantes:**")
                st.write(", ".join(ats_result["missing_skills"]) if ats_result["missing_skills"] else "Ninguna")
                st.write("**Coincidencias de palabras clave:**")
                matched_keywords = [k for k in job_data["keywords"] if k.lower() in [kw.lower() for kw in cv_data["keywords"]]]
                st.write(f"{ats_result['keyword_matches']} de {ats_result['total_keywords']}")
                st.write(", ".join(matched_keywords))
                st.write("**Palabras clave faltantes:**")
                st.write(", ".join(ats_result["missing_keywords"]) if ats_result["missing_keywords"] else "Ninguna")
                st.write("**Diferencia de experiencia:**")
                st.write(f"{ats_result['experience_gap']:.2f} años" if ats_result['experience_gap'] > 0 else "Cumples o superas la experiencia requerida")

        except Exception as e:
            log(f"Error: {e}")
            st.error(f"An unexpected error occurred: {e}")

# Manejo del fallo del scraping
if st.session_state["scraping_failed"]:
    st.warning("Error scraping page. Please paste the job description manually below and click 'Continue'.")
    st.session_state["manual_job_text"] = st.text_area(
        "Paste the job description here:",
        value=st.session_state["manual_job_text"]
    )

    if st.button("Continue with pasted description") and st.session_state["manual_job_text"].strip():
        st.session_state["continue_with_manual"] = True

if st.session_state.get("continue_with_manual") and st.session_state.get("manual_job_text", "").strip():
    with st.spinner("Processing with manual job description..."):
        try:
            job_description = st.session_state["manual_job_text"]
            job_data = extract_job_description_data(job_description, is_job=True)
            st.success("Job description data extracted successfully.")
            with open("file_outputs/job_description_data.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(job_data, ensure_ascii=False))

            extracted_text = extract_cv_text(st.session_state["uploaded_cv_path"])
            st.success("CV text extracted successfully.")
            with open("file_outputs/extracted_cv_text.txt", 'w', encoding='utf-8') as f:
                f.write(extracted_text)

            parsed_cv = parse_to_json_resume_sync(extracted_text)
            st.success("CV parsed successfully.")
            with open("file_outputs/resume.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(parsed_cv, ensure_ascii=False))

            cv_data = extract_job_description_data(extracted_text, is_job=False)
            st.success("CV data extracted successfully.")

            ats_result = calculate_ats_score_old(cv_data, job_data)
            st.success("ATS score calculated successfully.")

            # UI mejorada para modo manual
            st.subheader("Resultados del análisis ATS")
            st.metric("Puntaje ATS", f"{ats_result['score']}%", delta=None)

            tab1, tab2, tab3 = st.tabs(["Oferta laboral", "Tu CV", "Análisis ATS"])

            with tab1:
                st.write("**Habilidades requeridas:**")
                st.write(", ".join(job_data.get("skills", [])))
                st.write("**Palabras clave:**")
                st.write(", ".join(job_data.get("keywords", [])))
                st.write("**Experiencia mínima:**")
                st.write(f"{job_data.get('experience', 0)} años")
                st.write("**Idiomas:**")
                st.write(", ".join(job_data.get("languages", [])))

            with tab2:
                st.write("**Habilidades en tu CV:**")
                st.write(", ".join(cv_data.get("skills", [])))
                st.write("**Palabras clave:**")
                st.write(", ".join(cv_data.get("keywords", [])))
                st.write("**Experiencia estimada:**")
                st.write(f"{ats_result['resume_years']:.2f} años")
                st.write("**Idiomas:**")
                st.write(", ".join(cv_data.get("languages", [])))

            with tab3:
                st.write("**Coincidencias de habilidades:**")
                matched_skills = [s for s in job_data["skills"] if s.lower() in [sk.lower() for sk in cv_data["skills"]]]
                st.write(f"{ats_result['skill_matches']} de {ats_result['total_skills']}")
                st.write(", ".join(matched_skills))
                st.write("**Habilidades faltantes:**")
                st.write(", ".join(ats_result["missing_skills"]) if ats_result["missing_skills"] else "Ninguna")
                st.write("**Coincidencias de palabras clave:**")
                matched_keywords = [k for k in job_data["keywords"] if k.lower() in [kw.lower() for kw in cv_data["keywords"]]]
                st.write(f"{ats_result['keyword_matches']} de {ats_result['total_keywords']}")
                st.write(", ".join(matched_keywords))
                st.write("**Palabras clave faltantes:**")
                st.write(", ".join(ats_result["missing_keywords"]) if ats_result["missing_keywords"] else "Ninguna")
                st.write("**Diferencia de experiencia:**")
                st.write(f"{ats_result['experience_gap']:.2f} años" if ats_result['experience_gap'] > 0 else "Cumples o superas la experiencia requerida")

        except Exception as e:
            st.error(f"Error processing manual job description: {e}")