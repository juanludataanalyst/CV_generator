# CV Adapter - Planning Document

## Overview
This project converts a PDF CV into an ATS-friendly PDF by:
- Extracting text from the PDF using `pdfminer.six`
- Parsing the text into JSON Resume format via an LLM (e.g., Grok)
- Generating a minimalistic ATS-optimized PDF using `reportlab`

---

## Module Responsibilities

### `cv_extraction.py`
- Extract plain text from a PDF file using `pdfminer.six`.
- Function: `extract_cv_text(pdf_path: str) -> str`

### `cv_parser.py`
- Use an LLM to convert extracted text into JSON Resume format.
- Function: `parse_to_json_resume(text: str) -> dict`

### `ats_generator.py`
- Generate an ATS-friendly PDF from JSON Resume data.
- Function: `generate_ats_pdf(json_cv: dict, output_path: str) -> None`

### `main.py`
- Orchestrate the pipeline: extract → parse → generate.

---

## LLM Prompt Engineering

Example prompt to convert messy, unstructured CV text into JSON Resume:

```
You are an expert CV parser.

Given the following raw CV text extracted from a PDF, which may contain:
- Mixed sections (e.g., profile info mixed with experience)
- Repeated content across pages
- Sidebars or multi-column layouts
- Unordered or noisy data

Your task is to:
- Ignore duplicate or repeated sections
- Separate profile, experience, education, skills, and other sections clearly
- Deduplicate content across pages
- Preserve all original information without inventing or omitting details
- Output a clean, valid JSON Resume object following the schema at https://jsonresume.org/schema

CV Text:
"""
[PASTE EXTRACTED TEXT HERE]
"""
```

---

## Windows Considerations
- Use PowerShell-compatible commands for file operations.
- Ensure Python is added to PATH.
- Use `py -m pip` if `pip` command fails.
- Avoid command chaining with `&&`; use separate commands or `;`.

---

## Future Enhancements
- Add OCR fallback for scanned PDFs.
- Integrate job description adaptation.
- Develop a Streamlit UI.
- Agentize the editing process.
