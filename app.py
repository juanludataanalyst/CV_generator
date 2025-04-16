import streamlit as st
import os
import json
import glob
import shutil
import subprocess
from utils.utils import (
    extract_cv_text,
    parse_to_json_resume_sync,
    scrape_job_description,
    adapt_cv_to_job,
    extract_job_description_data,
    match_with_llm,
    calculate_ats_score_old,
    calculate_ats_score,
    adapt_cv_with_llm,
    convert_to_rendercv,
    generate_rendercv_pdf
)

# Configuración de la página
st.set_page_config(page_title="CV Adapter - ATS Optimizer", layout="centered")

# Estilo personalizado
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 5px; }
    .stTextInput>div>input { border-radius: 5px; }
    .stFileUploader { border-radius: 5px; }
    .stSpinner { color: #4CAF50; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: bold; }
    .metric-card { background-color: #ffffff; padding: 10px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .reportview-container { max-width: 800px; margin: auto; }
    .keyword-badge { display: inline-block; padding: 5px 10px; margin: 3px; border-radius: 12px; font-size: 14px; }
    .matched { background-color: #4CAF50; color: white; }
    .missing { background-color: #FF4D4F; color: white; }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.title("📄 CV Adapter - ATS Optimizer")
st.markdown("Optimize your CV to match job descriptions and improve your ATS score!")

# Inicializar estados en session_state
if "uploaded_cv_path" not in st.session_state:
    st.session_state["uploaded_cv_path"] = None
if "scraping_failed" not in st.session_state:
    st.session_state["scraping_failed"] = False
if "continue_with_manual" not in st.session_state:
    st.session_state["continue_with_manual"] = False
if "manual_job_text" not in st.session_state:
    st.session_state["manual_job_text"] = ""
if "yaml_path" not in st.session_state:
    st.session_state["yaml_path"] = None
if "pdf_path" not in st.session_state:
    st.session_state["pdf_path"] = None

# Layout en columnas para la subida de archivos y URL
col1, col2 = st.columns([1, 1])

with col1:
    # Subida del CV
    uploaded_file = st.file_uploader("📤 Upload your CV (PDF)", type=["pdf"])
    if uploaded_file and not st.session_state["uploaded_cv_path"]:
        with open("uploaded_cv.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state["uploaded_cv_path"] = "uploaded_cv.pdf"
        st.success("CV uploaded successfully!")

with col2:
    # Input de la URL
    job_url = st.text_input("🔗 Paste the job description URL", placeholder="e.g., https://jobs.example.com/123")

# Área de logs
log_area = st.empty()
logs = []

def log(msg):
    logs.append(msg)
    log_area.text("\n".join(logs[-20:]))

# Botón para iniciar el proceso
if (st.button("🚀 Generate ATS-optimized CV", use_container_width=True) 
    and st.session_state["uploaded_cv_path"] 
    and job_url 
    and not st.session_state["scraping_failed"] 
    and not st.session_state["continue_with_manual"]):
    with st.spinner("Processing your CV..."):
        log("Starting pipeline...")
        try:
            os.makedirs("file_outputs", exist_ok=True)

            # Extraer y guardar la descripción del trabajo
            job_description = scrape_job_description(job_url)
            st.success("Job description scraped")
            with open("file_outputs/job_description.txt", 'w', encoding='utf-8') as f:
                f.write(job_description)

            # Extraer datos de la oferta laboral
            job_data = extract_job_description_data(job_description, is_job=True)
            st.success("Job description data extracted")
            with open("file_outputs/job_description_data.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(job_data, ensure_ascii=False))

            # Extraer y guardar el texto del CV
            extracted_text = extract_cv_text(st.session_state["uploaded_cv_path"])
            with open("file_outputs/extracted_cv_text.txt", 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            st.success("CV text extracted.")

            # Parsear el CV a JSON
            parsed_cv = parse_to_json_resume_sync(extracted_text)
            with open("file_outputs/resume.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(parsed_cv, ensure_ascii=False))

            st.write("Standarizing CV ....")
            cv_data = extract_job_description_data(extracted_text, is_job=False)
            st.success("Original CV standardized ")

            keywords_match = match_with_llm(cv_data.get('keywords', []), job_data.get('keywords', []))

            # Análisis de palabras clave
            st.subheader("🔍 Keywords Analysis")
            col_match, col_miss = st.columns(2)
            with col_match:
                st.markdown("**Matched Keywords**")
                matched_keywords = keywords_match.get('matches', [])
                if matched_keywords:
                    badges = "".join([f"<span class='keyword-badge matched'>{kw}</span>" for kw in matched_keywords])
                    st.markdown(badges, unsafe_allow_html=True)
                else:
                    st.write("No matches")
            with col_miss:
                st.markdown("**Missing Keywords**")
                missing_keywords = keywords_match.get('missing', [])
                if missing_keywords:
                    badges = "".join([f"<span class='keyword-badge missing'>{kw}</span>" for kw in missing_keywords])
                    st.markdown(badges, unsafe_allow_html=True)
                else:
                    st.write("None missing")
            st.write(f"**Total Keyword Matches**: {len(matched_keywords)} of {len(job_data.get('keywords', []))}")

            # Calcular puntaje ATS inicial
            st.subheader("📊 ATS Scores")
            keywords_job = job_data.get('keywords', [])
            keywords_job_count = len(keywords_job) if keywords_job else 0
            score = calculate_ats_score(keywords_match, keywords_job_count)
            st.metric("ATS Score (Original CV)", f"{score}%")

            # Adaptar CV
            adapted_cv = adapt_cv_with_llm(parsed_cv, job_data, keywords_match)
            st.subheader("✨ Adapted CV")
            st.json(adapted_cv)

            # Extraer datos del CV adaptado
            cv_adapted_data_text = json.dumps(adapted_cv, indent=2)
            cv_adapted_data = extract_job_description_data(cv_adapted_data_text, is_job=False)

            # Calcular ATS score para el CV adaptado
            adapted_keywords_match = match_with_llm(cv_adapted_data.get('keywords', []), job_data.get('keywords', []))
            adapted_score = calculate_ats_score(adapted_keywords_match, keywords_job_count)

            col_new_match, col_new_miss = st.columns(2)
            with col_new_match:
                st.markdown("**Matched Keywords (Adapted CV)**")
                adapted_matched_keywords = adapted_keywords_match.get('matches', [])
                if adapted_matched_keywords:
                    badges = "".join([f"<span class='keyword-badge matched'>{kw}</span>" for kw in adapted_matched_keywords])
                    st.markdown(badges, unsafe_allow_html=True)
                else:
                    st.write("No matches")
            with col_new_miss:
                st.markdown("**Missing Keywords (Adapted CV)**")
                adapted_missing_keywords = adapted_keywords_match.get('missing', [])
                if adapted_missing_keywords:
                    badges = "".join([f"<span class='keyword-badge missing'>{kw}</span>" for kw in adapted_missing_keywords])
                    st.markdown(badges, unsafe_allow_html=True)
                else:
                    st.write("None missing")
            st.write(f"**Total Keyword Matches (Adapted CV)**: {len(adapted_matched_keywords)} of {len(job_data.get('keywords', []))}")

            # Mostrar puntajes ATS
            st.metric("ATS Score (Adapted CV)", f"{adapted_score}%")
            st.metric("Improvement in ATS Score", f"{adapted_score - score:.2f}%", delta_color="normal")

            # Calcular puntaje ATS antiguo
            ats_result = calculate_ats_score_old(cv_data, job_data)
            st.success("ATS analysis completed successfully.")

            # Nueva interfaz con pestañas
            st.subheader("📑 Detailed ATS Analysis")
            tab1, tab2, tab3 = st.tabs(["Job Description", "Your CV", "ATS Insights"])

            with tab1:
                st.markdown("### Job Description Keywords")
                keywords = job_data.get("keywords", [])
                if keywords:
                    badges = "".join([f"<span class='keyword-badge matched'>{kw}</span>" for kw in keywords])
                    st.markdown(badges, unsafe_allow_html=True)
                else:
                    st.write("No keywords specified")

            with tab2:
                st.markdown("### Your CV Keywords")
                keywords = cv_data.get("keywords", [])
                if keywords:
                    badges = "".join([f"<span class='keyword-badge matched'>{kw}</span>" for kw in keywords])
                    st.markdown(badges, unsafe_allow_html=True)
                else:
                    st.write("No keywords detected")

            with tab3:
                st.markdown("### ATS Keyword Insights")
                col_keywords = st.columns(1)[0]
                with col_keywords:
                    st.markdown("**Keyword Matches**")
                    matched_keywords = [k for k in job_data["keywords"] if k.lower() in [kw.lower() for kw in cv_data["keywords"]]]
                    st.write(f"{ats_result['keyword_matches']} of {ats_result['total_keywords']}")
                    if matched_keywords:
                        badges = "".join([f"<span class='keyword-badge matched'>{kw}</span>" for kw in matched_keywords])
                        st.markdown(badges, unsafe_allow_html=True)
                    else:
                        st.write("None")
                    st.markdown("**Missing Keywords**")
                    if ats_result["missing_keywords"]:
                        badges = "".join([f"<span class='keyword-badge missing'>{kw}</span>" for kw in ats_result["missing_keywords"]])
                        st.markdown(badges, unsafe_allow_html=True)
                    else:
                        st.write("None")

            st.write("Creating new CV...")

            # Convert to RenderCV YAML
            log("Converting to YAML for RenderCV...")
            yaml_path = convert_to_rendercv(adapted_cv, output_dir="rendercv_output", theme="classic")
            log(f"RenderCV YAML generated at: {yaml_path}")

            # Generate PDF
            log("Generating PDF...")
            pdf_path = generate_rendercv_pdf(yaml_path, output_dir="rendercv_output", final_pdf_name="adapted_cv.pdf")
            log(f"PDF generated at: {pdf_path}")

            # Guardar los paths en session_state
            st.session_state["yaml_path"] = yaml_path
            st.session_state["pdf_path"] = pdf_path

            st.success("CV generated successfully!")

        except Exception as e:
            log(f"Error: {e}")
            st.error(f"An unexpected error occurred: {e}")

# Mostrar botones de descarga si los archivos existen
if st.session_state.get("yaml_path") and os.path.exists(st.session_state["yaml_path"]):
    with open(st.session_state["yaml_path"], "r", encoding="utf-8") as f:
        yaml_content = f.read()
        st.download_button(
            label="Download YAML file (for editing)",
            data=yaml_content,
            file_name="cv.yaml",
            mime="text/yaml",
            key="download_yaml"
        )

if st.session_state.get("pdf_path") and os.path.exists(st.session_state["pdf_path"]):
    with open(st.session_state["pdf_path"], "rb") as f:
        pdf_content = f.read()
        st.download_button(
            label="Download new CV",
            data=pdf_content,
            file_name="adapted_cv.pdf",
            mime="application/pdf",
            key="download_pdf"
        )