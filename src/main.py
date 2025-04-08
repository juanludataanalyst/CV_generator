from cv_extraction import extract_cv_text
from cv_parser import parse_to_json_resume
import json

def main():
    """
    Paso 1: Extraer texto del CV en PDF (Resume.pdf).
    Paso 2: Convertir el texto a JSON Resume usando LLM.
    """
    pdf_cv_path = "Resume.pdf"

    # Paso 1: Extracción
    cv_text = extract_cv_text(pdf_cv_path)

    if not cv_text:
        print("Error: No se pudo extraer texto del CV.")
        return

    print("\n--- Texto extraído (primeros 500 caracteres) ---\n")
    print(cv_text[:500])
    print("\n--- Fin del extracto ---\n")

    with open("cv_text.txt", "w", encoding="utf-8") as f:
        f.write(cv_text)
    print("Texto completo guardado en cv_text.txt")

    # Paso 2: Parsing a JSON Resume
    try:
        json_cv = parse_to_json_resume(cv_text)
    except Exception as e:
        print(f"Error al parsear el CV a JSON: {e}")
        return

    # Mostrar parte del JSON para inspección
    print("\n--- JSON Resume generado (primeros 500 caracteres) ---\n")
    json_preview = json.dumps(json_cv, ensure_ascii=False, indent=2)[:500]
    print(json_preview)
    print("\n--- Fin del extracto JSON ---\n")

    # Guardar JSON completo
    with open("parsed_resume.json", "w", encoding="utf-8") as f:
        json.dump(json_cv, f, ensure_ascii=False, indent=2)
    print("JSON Resume guardado en parsed_resume.json")

if __name__ == "__main__":
    main()
