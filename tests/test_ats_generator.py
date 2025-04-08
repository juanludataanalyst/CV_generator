import json
from src.ats_generator import generate_ats_pdf

def test_generate_pdf():
    """
    Prueba la función generate_ats_pdf con un JSON Resume de ejemplo.
    """
    input_json_path = ".adapted_resume.json"
    output_pdf_path = ".test_output.pdf"

    try:
        with open(input_json_path, "r", encoding="utf-8") as f:
            json_cv = json.load(f)
    except FileNotFoundError:
        print(f"Archivo {input_json_path} no encontrado. Asegúrate de tener un JSON Resume válido.")
        return

    try:
        generate_ats_pdf(json_cv, output_pdf_path)
        print(f"PDF generado correctamente en {output_pdf_path}")
    except Exception as e:
        print(f"Error al generar el PDF: {e}")

if __name__ == "__main__":
    test_generate_pdf()
