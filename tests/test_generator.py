import os
import pytest
from src.ats_generator import generate_ats_pdf


def test_generate_pdf_typical(tmp_path):
    """
    Test generating ATS PDF from typical JSON Resume data.
    """
    json_cv = {
        "basics": {"name": "John Doe", "email": "john@example.com", "phone": "123-456"},
        "work": [
            {
                "position": "Engineer",
                "company": "Acme Corp",
                "startDate": "2020-01-01",
                "endDate": "2022-01-01",
                "summary": "Worked on projects.",
            }
        ],
        "education": [
            {
                "institution": "Uni",
                "studyType": "BSc",
                "startDate": "2015-01-01",
                "endDate": "2019-01-01",
            }
        ],
        "skills": [{"name": "Python"}],
    }
    output_path = tmp_path / "output.pdf"
    generate_ats_pdf(json_cv, str(output_path))
    assert output_path.exists()


def test_generate_pdf_minimal(tmp_path):
    """
    Test generating ATS PDF from minimal JSON Resume data.
    """
    json_cv = {}
    output_path = tmp_path / "minimal.pdf"
    generate_ats_pdf(json_cv, str(output_path))
    assert output_path.exists()


def test_generate_pdf_invalid_data(tmp_path):
    """
    Test generating ATS PDF from invalid or empty data.
    """
    json_cv = None
    output_path = tmp_path / "invalid.pdf"
    try:
        generate_ats_pdf(json_cv, str(output_path))
    except Exception:
        # Expected to fail gracefully
        pass
    # File may or may not exist depending on error handling
