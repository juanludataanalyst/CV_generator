from cv_extraction import extract_cv_text
from cv_parser import parse_to_json_resume, get_model
from job_scraper import scrape_job_description
from job_to_cv_parser import adapt_cv_to_job
from json_to_rendercv_yaml import convert
from pydantic_ai import Agent
import json

def main():
    """
    Pipeline:
    1. Extract text from the PDF CV.
    2. Convert extracted text to JSON Resume format.
    3. Ask for the job description URL and extract its content.
    4. Adapt the CV to the job description using the ATS optimization system.
    """
    pdf_cv_path = "Resume.pdf"

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
        json_cv = parse_to_json_resume(cv_text)
    except Exception as e:
        print(f"Error parsing CV to JSON: {e}")
        return

    with open("parsed_resume.json", "w", encoding="utf-8") as f:
        json.dump(json_cv, f, ensure_ascii=False, indent=2)
    print("JSON Resume saved to parsed_resume.json")

    # Step 3: Ask for job description URL and extract content
    url = input("Enter the job description URL: ").strip()
    agent = Agent(get_model())
    job_description = scrape_job_description(url, agent)

    if job_description.startswith("Error"):
        print(f"Error fetching job description: {job_description}")
        return

    with open("job_description.txt", "w", encoding="utf-8") as f:
        f.write(job_description)
    print("Job description saved to job_description.txt")

    # Step 4: Adapt the CV to the job description using ATS optimization
    try:
        adapted_cv = adapt_cv_to_job(json_cv, job_description)
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

if __name__ == "__main__":
    main()
