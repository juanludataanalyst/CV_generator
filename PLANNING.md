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

Example prompt to convert plain CV text to JSON Resume:

```
Convert the following CV text into a JSON Resume format (https://jsonresume.org/schema). Preserve all original content without adding or removing information.

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
