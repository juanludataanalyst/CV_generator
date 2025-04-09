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

def run_llm(agent, prompt):
    return asyncio.run(agent.run(prompt))

def get_model():
    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    base_url = "https://openrouter.ai/api/v1"
    model_name = "openrouter/quasar-alpha"
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIModel(model_name, provider=provider)

def run_pipeline(pdf_path: str, job_url: str, log_callback=None):
    """
    Run the full CV adaptation pipeline.

    Args:
        pdf_path (str): Path to the uploaded CV PDF.
        job_url (str): URL of the job description.
        log_callback (callable, optional): Function to log messages.
    """
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

    log("Scraping job description...")
    job_description = scrape_job_description(job_url, agent)

    log("Adapting CV to job description...")
    adapted_cv = adapt_cv_to_job(json_cv, job_description, agent)

    log("Saving adapted CV ...")
    with open("adapted_resume.json", "w", encoding="utf-8") as f:
        json.dump(adapted_cv, f, indent=2, ensure_ascii=False)

    log("Converting for render..")
    convert("adapted_resume.json", "cv_rendercv.yaml")

    import glob
    import shutil

    log("Generating final PDF...")
    try:
        result = subprocess.run(
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
