from src.cv_extraction import extract_cv_text
from src.cv_parser import parse_to_json_resume
from src.job_scraper import scrape_job_description
from src.job_to_cv_parser import adapt_cv_to_job
from src.json_to_rendercv_yaml import convert
from pydantic_ai import Agent
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
import subprocess
import json
import os
import asyncio
import streamlit as st

def run_llm(agent, prompt):
    return asyncio.run(agent.run(prompt))

def get_model():
    api_key = st.secrets["OPENROUTER_API_KEY"]
    base_url = "https://openrouter.ai/api/v1"
    model_name = "openrouter/quasar-alpha"
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIModel(model_name, provider=provider)

def run_pipeline(pdf_path: str, job_url: str = None, job_text: str = None, log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    log("Extracting text from PDF...")
    cv_text = extract_cv_text(pdf_path)

    agent = Agent(get_model())

    log("Parsing CV to JSON Resume...")
    json_cv = parse_to_json_resume(cv_text, agent)

    if job_text:
        log("Using manual job description provided by user.")
    else:
        log("Scraping job description...")
        job_text = scrape_job_description(job_url, agent, log_callback=log)
        if job_text.startswith("Error"):
            return {"error": "scraping_failed"}

    return _run_pipeline_core(cv_text, job_text, agent, log)

def _run_pipeline_core(cv_text, job_text, agent, log):
    log("Adapting CV to job description...")
    adapted_cv, initial_match, final_match, initial_score, final_score = adapt_cv_to_job(
        parse_to_json_resume(cv_text, agent),
        job_text,
        agent
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
