from src.cv_extraction import extract_cv_text
from src.cv_parser import parse_to_json_resume
from src.job_scraper import scrape_job_description
from src.job_to_cv_parser import adapt_cv_to_job
from src.json_to_rendercv_yaml import convert
import subprocess
import json
import os
import streamlit as st


# Configuración del cliente OpenAI para OpenRouter
client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"]
)

def run_llm(prompt):
    response = client.chat.completions.create(
        model="openrouter/quasar-alpha",
        messages=[
            {"role": "system", "content": "You are an expert assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def run_pipeline(pdf_path: str, job_url: str = None, job_text: str = None, log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    log("Extracting text from PDF...")
    cv_text = extract_cv_text(pdf_path)

    log("Parsing CV to JSON Resume...")
    json_cv = parse_to_json_resume(cv_text)

    if job_text:
        log("Using manual job description provided by user.")
    else:
        log("Scraping job description...")
        job_text = scrape_job_description(job_url, None, log_callback=log)
        if job_text.startswith("Error"):
            return {"error": "scraping_failed"}

    return _run_pipeline_core(cv_text, job_text, None, log)

def _run_pipeline_core(cv_text, job_text, _, log):
    log("Adapting CV to job description...")
    adapted_cv, initial_match, final_match, initial_score, final_score = adapt_cv_to_job(
        parse_to_json_resume(cv_text, None),
        job_text,
        None
    )

    log("Saving adapted CV JSON...")
    with open("adapted_resume.json", "w", encoding="utf-8") as f:
        json.dump(adapted_cv, f, indent=2, ensure_ascii=False)

    log("Converting to YAML for RenderCV...")
    convert("adapted_resume.json", "cv_rendercv.yaml")

    import glob
    import shutil

    log("Generating final PDF with RenderCV CLI...")
    try:
        subprocess.run(
            ["rendercv", "render", "cv_rendercv.yaml"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        log(f"RenderCV failed with exit code {e.returncode}")
        log(f"STDOUT:\n{e.stdout}")
        log(f"STDERR:\n{e.stderr}")
        raise

    log("Finding generated PDF...")
    pdf_files = glob.glob("rendercv_output/*.pdf")
    if not pdf_files:
        raise FileNotFoundError("No PDF generated in rendercv_output/")
    latest_pdf = max(pdf_files, key=os.path.getmtime)

    log("Copying final PDF to final_cv.pdf")
    shutil.copy(latest_pdf, "final_cv.pdf")

    return {
        "initial_score": initial_score,
        "final_score": final_score,
        "initial_match": initial_match,
        "final_match": final_match
    }

