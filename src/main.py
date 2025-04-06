import json
from cv_extraction import extract_cv_text
from cv_parser import parse_to_json_resume
from ats_generator import generate_ats_pdf


def main():
    """
    Main pipeline to convert a PDF CV into an ATS-friendly PDF.
    """
    try:
        with open("../parsed_resume.json", "r", encoding="utf-8") as f:
            json_cv = json.load(f)
        output_path = "../output.pdf"
        generate_ats_pdf(json_cv, output_path)
        print(f"ATS CV generated at {output_path}")
    except FileNotFoundError:
        print("Error: parsed_resume.json not found.")
    except json.JSONDecodeError as e:
        print(f"Error decoding parsed_resume.json: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
