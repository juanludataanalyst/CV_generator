from cv_extraction import extract_cv_text

def main():
    """
    Paso 1: Extraer texto del CV en PDF (Resume.pdf) y mostrarlo.
    """
    pdf_cv_path = "Resume.pdf"

    cv_text = extract_cv_text(pdf_cv_path)

    if not cv_text:
        print("Error: No se pudo extraer texto del CV.")
        return

    # Mostrar los primeros 500 caracteres para inspección rápida
    print("\n--- Texto extraído (primeros 500 caracteres) ---\n")
    print(cv_text[:500])
    print("\n--- Fin del extracto ---\n")

    # Guardar el texto completo para revisión
    with open("cv_text.txt", "w", encoding="utf-8") as f:
        f.write(cv_text)
    print("Texto completo guardado en cv_text.txt")

if __name__ == "__main__":
    main()
