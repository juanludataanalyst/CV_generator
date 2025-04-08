from pdfminer.high_level import extract_text


def extract_cv_text(pdf_path: str) -> str:
    """
    Extracts text from a PDF CV file using pdfminer.six.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted plain text from the CV.
    """
    try:
        text = extract_text(pdf_path)
        with open("prueba", 'w', encoding='utf-8') as archivo:
            archivo.writelines(text)
        return text
    except Exception as e:
        # Reason: Extraction might fail on corrupt or encrypted PDFs
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""
