# CV Adapter - ATS Optimizer

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-%23FF4B4B.svg?style=flat&logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-green)

---

## Descripción

**CV Adapter - ATS Optimizer** es una aplicación que adapta y optimiza tu currículum (CV) para que coincida con una oferta de trabajo específica, maximizando el puntaje ATS (Applicant Tracking System). Utiliza inteligencia artificial para analizar y reescribir tu CV, resaltando las habilidades y palabras clave más relevantes para cada puesto.

---

## Características principales

- **Carga de CV en PDF**: Extrae y convierte tu CV a formato estructurado (JSON Resume).
- **Obtención de oferta laboral**: Ingresa una URL o el texto de la oferta y la app extrae los requisitos clave automáticamente.
- **Análisis y adaptación inteligente**: Compara skills, keywords y experiencia entre tu CV y la oferta. Adapta el CV para maximizar la coincidencia.
- **Cálculo de puntaje ATS**: Muestra el porcentaje de compatibilidad antes y después de la optimización.
- **Generación de archivos**: Descarga tu CV adaptado en PDF, HTML o YAML listo para RenderCV.
- **Integración con Google Drive**: Sube tu CV adaptado directamente a tu cuenta de Google Drive.

---

## Instalación

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/tuusuario/CV_generator.git
   cd CV_generator
   ```
2. **Crea y activa un entorno virtual (opcional):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```
3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Uso rápido

1. **Lanza la aplicación:**
   ```bash
   streamlit run app.py
   ```
2. **Sigue los pasos en la interfaz web:**
   - Sube tu CV en PDF.
   - Ingresa la URL o el texto de la oferta laboral.
   - Haz clic en "Generate ATS-optimized CV".
   - Descarga tu CV optimizado o súbelo a Google Drive.

---

## Ejemplo de flujo

<details>
<summary>Ver ejemplo paso a paso</summary>

1. Sube tu archivo `Resume.pdf`.
2. Ingresa la URL de una oferta de trabajo de LinkedIn o pega el texto.
3. El sistema extrae y analiza los requisitos.
4. Se adapta tu CV y se calcula el puntaje ATS.
5. Descarga el PDF optimizado.

</details>

---

## Estructura del proyecto

```
CV_generator/
├── app.py                   # Interfaz principal Streamlit
├── pipeline.py              # Lógica del pipeline principal
├── src/                     # Módulos de procesamiento
│   ├── cv_extraction.py
│   ├── cv_parser.py
│   ├── job_scraper.py
│   ├── job_to_cv_parser.py
│   ├── json_to_rendercv_yaml.py
│   ├── models.py
│   └── generate_cv.py
├── utils/                   # Utilidades y helpers
│   └── utils.py
├── tests/                   # Pruebas unitarias
├── requirements.txt         # Dependencias
├── README.md                # Este archivo
└── ...                      # Otros archivos y salidas
```

---

## Variables de entorno y configuración

- Para usar la integración con modelos LLM y Google Drive, configura tus claves en el archivo `secrets.toml` de Streamlit.
- Ejemplo:
  ```toml
  OPENROUTER_API_KEY = "tu_clave_openrouter"
  token_pickle_b64 = "..."
  client_secret_json = "..."
  ```

---

## Contribuir

¡Las contribuciones son bienvenidas! Abre un issue o un pull request para sugerir mejoras, nuevas funciones o reportar bugs.

---

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.

---

## Créditos y agradecimientos

- Inspirado por las mejores prácticas de optimización de CV y ATS.
- Utiliza [Streamlit](https://streamlit.io/), [OpenAI](https://openai.com/), [RenderCV](https://github.com/mauriciogtec/rendercv) y otras librerías open-source.

---
