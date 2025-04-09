from cv_extraction import extract_cv_text
from cv_parser import parse_to_json_resume
from job_scraper import scrape_job_description
from job_to_cv_parser import adapt_cv_to_job
from json_to_rendercv_yaml import convert
from pydantic_ai import Agent
from dotenv import load_dotenv
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
import os
import json
import subprocess

load_dotenv()

def get_model():
    """
    Configura el modelo de OpenRouter sin parámetros adicionales en el constructor.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    base_url = "https://openrouter.ai/api/v1"
    model_name = "openrouter/quasar-alpha"
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIModel(model_name=model_name, provider=provider)

def main():
    """
    Pipeline:
    1. Extract text from the PDF CV.
    2. Convert extracted text to JSON Resume format.
    3. Ask for the job description URL and extract its content.
    4. Adapt the CV to the job description using the ATS optimization system.
    """
    pdf_cv_path = "TimResume.pdf"

    # Create the LLM agent with seed and temperature in model_settings
    agent = Agent(
        model=get_model(),
        model_settings={"seed": 42, "temperature": 0.5}  # Pasamos seed y temperature aquí
    )

    # Step 1: Extract text from PDF CV
    cv_text = extract_cv_text(pdf_cv_path)
    if not cv_text:
        print("Error: Failed to extract text from the CV.")
        return

    with open("cv_text.txt", "w", encoding="utf-8") as f:
        f.write(cv_text)
    print("Full extracted text saved to cv_text.txt")

    # Step 2: Convert text to JSON Resume
    try:
        json_cv = parse_to_json_resume(cv_text, agent)
    except Exception as e:
        print(f"Error parsing CV to JSON: {e}")
        return

    with open("parsed_resume.json", "w", encoding="utf-8") as f:
        json.dump(json_cv, f, ensure_ascii=False, indent=2)
    print("JSON Resume saved to parsed_resume.json")

    # Step 3: Define job description URL and extract content
    url = "https://consensys.io/open-roles/6741051?source=web3.career"  # Set your job description URL here
    job_description = scrape_job_description(url, agent)

    if job_description.startswith("Error"):
        print(f"Error fetching job description: {job_description}")
        return

    with open("job_description.txt", "w", encoding="utf-8") as f:
        f.write(job_description)
    print("Job description saved to job_description.txt")

    # Step 4: Adapt the CV to the job description using ATS optimization
    try:
        adapted_cv, initial_match, final_match, initial_score, final_score = adapt_cv_to_job(json_cv, job_description, agent)
    except Exception as e:
        print(f"Error adapting CV to the job description: {e}")
        return

    with open("adapted_resume.json", "w", encoding="utf-8") as f:
        json.dump(adapted_cv, f, ensure_ascii=False, indent=2)
    print("Adapted CV saved to adapted_resume.json")

    print(f"Final ATS Match Score: {adapted_cv.get('ats_match_score', 'N/A')}%")

    # Convert adapted_resume.json to YAML for RenderCV
    convert("adapted_resume.json", "cv_rendercv.yaml")
    print("Converted adapted_resume.json to cv_rendercv.yaml")

    # Generate final PDF with RenderCV CLI
    try:
        subprocess.run(["rendercv", "render", "cv_rendercv.yaml"], check=True)
        print("Final PDF generated.")
    except Exception as e:
        print(f"Error generating final PDF: {e}")

if __name__ == "__main__":
    main()
