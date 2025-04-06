import pytest
from src.cv_extraction import extract_cv_text


def test_extract_valid_pdf():
    """
    Test extraction from a well-formatted, valid PDF.
    """
    # TODO: Provide a sample valid PDF path
    pdf_path = "../input_cv.pdf"
    text = extract_cv_text(pdf_path)
    # This will pass once a real PDF is provided
    assert isinstance(text, str)


def test_extract_empty_pdf():
    """
    Test extraction from an empty or unreadable PDF.
    """
    # TODO: Provide a path to an empty or corrupt PDF
    pdf_path = "../empty_or_corrupt.pdf"
    text = extract_cv_text(pdf_path)
    assert text == ""


def test_extract_disordered_text_pdf():
    """
    Test extraction from a PDF with disordered or complex layout text.
    """
    # TODO: Provide a sample disordered text PDF
    pdf_path = "../disordered_text.pdf"
    text = extract_cv_text(pdf_path)
    # For now, just check it returns a string
    assert isinstance(text, str)
