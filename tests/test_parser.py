import pytest
from src.cv_parser import parse_to_json_resume


def test_parse_typical_cv_text():
    """
    Test parsing typical CV plain text.
    """
    sample_text = "John Doe\nSoftware Engineer\njohn@example.com"
    json_resume = parse_to_json_resume(sample_text)
    assert isinstance(json_resume, dict)
    assert "basics" in json_resume


def test_parse_minimal_text():
    """
    Test parsing minimal or unusual CV text.
    """
    minimal_text = "Jane"
    json_resume = parse_to_json_resume(minimal_text)
    assert isinstance(json_resume, dict)


def test_parse_empty_text():
    """
    Test parsing empty input text.
    """
    empty_text = ""
    json_resume = parse_to_json_resume(empty_text)
    assert isinstance(json_resume, dict)
