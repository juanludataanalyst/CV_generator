from cv_extraction import extract_cv_text
from cv_parser import parse_to_json_resume, get_model
from job_scraper import scrape_job_description
from job_to_cv_parser import adapt_cv_to_job
from pydantic_ai import Agent
import json

def main():
    """
    Paso 1: Extraer texto del CV en PDF (Resume.pdf).
    Paso 2: Convertir el texto a JSON Resume usando LLM.
    Paso 3: Pedir URL de oferta laboral y extraer descripción.
    Paso 4: Adaptar el CV a la oferta con un score objetivo.
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

    print("\n--- JSON Resume generado (primeros 500 caracteres) ---\n")
    json_preview = json.dumps(json_cv, ensure_ascii=False, indent=2)[:500]
    print(json_preview)
    print("\n--- Fin del extracto JSON ---\n")

    with open("parsed_resume.json", "w", encoding="utf-8") as f:
        json.dump(json_cv, f, ensure_ascii=False, indent=2)
    print("JSON Resume guardado en parsed_resume.json")

    # Paso 3: Pedir URL y extraer descripción de la oferta
    url = input("Introduce la URL de la oferta laboral: ").strip()
    agent = Agent(get_model())
    job_description = scrape_job_description(url, agent)

    if job_description.startswith("Error"):
        print(f"Error al obtener la oferta laboral: {job_description}")
        return

    print("\n--- Descripción de la oferta (primeros 500 caracteres) ---\n")
    print(job_description[:500])
    print("\n--- Fin del extracto descripción ---\n")

    with open("job_description.txt", "w", encoding="utf-8") as f:
        f.write(job_description)
    print("Descripción de la oferta guardada en job_description.txt")

    # Paso 4: Pedir score objetivo y adaptar el CV
    try:
        score = int(input("Introduce el score objetivo (ej. 90): ").strip())
    except ValueError:
        print("Score inválido, usando 100 por defecto.")
        score = 100

    try:
        adapted_cv = adapt_cv_to_job(json_cv, job_description, score)
    except Exception as e:
        print(f"Error al adaptar el CV a la oferta: {e}")
        return

    # Mostrar y guardar el CV adaptado
    print("\n--- CV adaptado (primeros 500 caracteres) ---\n")
    adapted_preview = json.dumps(adapted_cv, ensure_ascii=False, indent=2)[:500]
    print(adapted_preview)
    print("\n--- Fin del extracto CV adaptado ---\n")

    with open("adapted_resume.json", "w", encoding="utf-8") as f:
        json.dump(adapted_cv, f, ensure_ascii=False, indent=2)
    print("CV adaptado guardado en adapted_resume.json")

if __name__ == "__main__":
    main()
