from cv_extraction import extract_cv_text
from cv_parser import parse_to_json_resume
from ats_generator import generate_ats_pdf


def main():
    """
    Main pipeline to convert a PDF CV into an ATS-friendly PDF.
    """
    pdf_path = "../input_cv.pdf"
    output_path = "../output_cv.pdf"

    text = extract_cv_text(pdf_path)
    json_cv = parse_to_json_resume(text)
    generate_ats_pdf(json_cv, output_path)

    print(f"ATS CV generated at {output_path}")


if __name__ == "__main__":
    main()
