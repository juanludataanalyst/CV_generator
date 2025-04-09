import streamlit as st
import os
import json
import glob
import shutil
import subprocess
from pipeline import run_pipeline

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
            results = run_pipeline(st.session_state["uploaded_cv_path"], job_url, log_callback=log)
            if "error" in results and results["error"] == "scraping_failed":
                st.session_state["scraping_failed"] = True
                log("Scraping failed. Please provide the job description manually.")
                st.error("Failed to scrape the job description from the URL.")
            else:
                with open("final_cv.pdf", "rb") as f:
                    pdf_bytes = f.read()
                st.success("Done! Download your adapted CV below.")
                st.download_button("Download adapted CV", data=pdf_bytes, file_name="Adapted_CV.pdf", mime="application/pdf")
        except Exception as e:
            log(f"Error: {e}")
            st.error(f"An unexpected error occurred: {e}")

# Manejo del fallo del scraping
if st.session_state["scraping_failed"] and not st.session_state["continue_with_manual"]:
    st.warning("Error scraping page. Please paste the job description manually below and click 'Continue'.")
    st.session_state["manual_job_text"] = st.text_area(
        "Paste the job description here:",
        value=st.session_state["manual_job_text"]
    )
    if st.button("Continue with pasted description") and st.session_state["manual_job_text"].strip():
        st.session_state["continue_with_manual"] = True

# Procesamiento con descripción manual
if st.session_state["continue_with_manual"] and st.session_state["uploaded_cv_path"]:
    with st.spinner("Processing with manual job description..."):
        # Extraer texto del CV
        from src.cv_parser import extract_cv_text
        cv_text = extract_cv_text(st.session_state["uploaded_cv_path"])

        # Inicializar agente
        agent = None
        try:
            from pipeline import get_model
            from pydantic_ai import Agent as PAgent
            agent = PAgent(get_model())
        except Exception as e:
            st.error(f"Error initializing agent: {e}")
            st.stop()

        # Parsear CV a JSON
        from src.cv_parser import parse_to_json_resume
        json_cv = parse_to_json_resume(cv_text, agent)

        # Adaptar CV
        from src.job_to_cv_parser import adapt_cv_to_job
        adapted_cv, initial_match, final_match, initial_score, final_score = adapt_cv_to_job(
            json_cv, st.session_state["manual_job_text"], agent
        )

        # Guardar JSON adaptado
        with open("adapted_resume.json", "w", encoding="utf-8") as f:
            json.dump(adapted_cv, f, indent=2, ensure_ascii=False)

        # Convertir a YAML
        from src.json_to_rendercv_yaml import convert
        convert("adapted_resume.json", "cv_rendercv.yaml")

        # Generar PDF
        try:
            subprocess.run(["rendercv", "render", "cv_rendercv.yaml"], check=True)
            pdf_files = glob.glob("rendercv_output/*.pdf")
            if not pdf_files:
                st.error("No PDF generated.")
                st.stop()
            latest_pdf = max(pdf_files, key=os.path.getmtime)
            shutil.copy(latest_pdf, "final_cv.pdf")
            with open("final_cv.pdf", "rb") as f:
                pdf_bytes = f.read()
            st.success("Done! Download your adapted CV below.")
            st.download_button("Download adapted CV", data=pdf_bytes, file_name="Adapted_CV.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
