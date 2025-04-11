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
    calculate_ats_score
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


            # Calcular el puntaje ATS usando el CV parseado y los datos de la oferta
            ats_result = calculate_ats_score(cv_data, job_data)
            st.success("ATS score calculated successfully.")
            st.json(ats_result)  # Mostrar el resultado en la interfaz
            print(ats_result)

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
            parsed_cv = parse_to_json_resume_sync(extracted_text)
            ats_result = calculate_ats_score(parsed_cv, job_data)
            st.success("ATS score calculated successfully.")
            st.json(ats_result)
        except Exception as e:
            st.error(f"Error processing manual job description: {e}")