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

def run_pipeline(pdf_path: str, job_url: str):
    """
    Run the full CV adaptation pipeline.

    Args:
        pdf_path (str): Path to the uploaded CV PDF.
        job_url (str): URL of the job description.
    """
    # 1. Extract text from PDF
    cv_text = extract_cv_text(pdf_path)

    # 2. Create LLM agent
    agent = Agent(get_model())

    # 3. Parse text to JSON Resume
    json_cv = parse_to_json_resume(cv_text, agent)

    # 4. Scrape job description
    job_description = scrape_job_description(job_url, agent)

    # 5. Adapt CV to job description
    adapted_cv = adapt_cv_to_job(json_cv, job_description, agent)

    # 6. Save adapted CV JSON
    with open("adapted_resume.json", "w", encoding="utf-8") as f:
        json.dump(adapted_cv, f, indent=2, ensure_ascii=False)

    # 7. Convert to YAML for RenderCV
    convert("adapted_resume.json", "cv_rendercv.yaml")

    import glob
    import shutil

    # 8. Generate final PDF with RenderCV CLI
    try:
        result = subprocess.run(
            ["rendercv", "render", "cv_rendercv.yaml"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print("RenderCV failed with exit code", e.returncode)
        print("STDOUT:\n", e.stdout)
        print("STDERR:\n", e.stderr)
        raise

    # 9. Find the generated PDF in rendercv_output/
    pdf_files = glob.glob("rendercv_output/*.pdf")
    if not pdf_files:
        raise FileNotFoundError("No PDF generated in rendercv_output/")
    latest_pdf = max(pdf_files, key=os.path.getmtime)

    # 10. Copy or move it to final_cv.pdf
    shutil.copy(latest_pdf, "final_cv.pdf")
