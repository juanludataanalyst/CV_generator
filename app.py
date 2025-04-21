import streamlit as st
import os
import json
import glob
import shutil
import subprocess
import requests
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
    generate_rendercv_pdf,
    get_discard_messages,
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
    .warning-message { background-color: #FFF3CD; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
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
if "job_url" not in st.session_state:
    st.session_state["job_url"] = ""
if "discard_messages" not in st.session_state:
    st.session_state["discard_messages"] = []

# Subida del CV
uploaded_file = st.file_uploader("📤 Upload your CV (PDF)", type=["pdf"])
if uploaded_file and not st.session_state["uploaded_cv_path"]:
    with open("uploaded_cv.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.session_state["uploaded_cv_path"] = "uploaded_cv.pdf"
    st.session_state["scraping_failed"] = False
    st.session_state["continue_with_manual"] = False
    st.session_state["manual_job_text"] = ""
    st.session_state["yaml_path"] = None
    st.session_state["pdf_path"] = None
    st.session_state["discard_messages"] = []
    st.success("CV uploaded successfully!")

# Input de la URL
job_url = st.text_input("🔗 Paste the job description URL", value=st.session_state["job_url"], placeholder="e.g., https://jobs.example.com/123")
st.session_state["job_url"] = job_url

# Función para organizar mensajes de descarte por categoría
def organize_discard_messages(messages):
    categories = {
        "Dates": [],
        "Phone": [],
        "Email": [],
        "URL": [],
        "Location": [],
        "Social Networks": [],
        "Summary": [],
        "Skills": [],
        "Projects": [],
        "Languages": [],
        "Other": []
    }
    for msg in messages:
        if "Date" in msg or "start_date" in msg or "end_date" in msg:
            categories["Dates"].append(msg)
        elif "Phone" in msg:
            categories["Phone"].append(msg)
        elif "Email" in msg:
            categories["Email"].append(msg)
        elif "URL" in msg or "website" in msg:
            categories["URL"].append(msg)
        elif "Location" in msg or "location" in msg:
            categories["Location"].append(msg)
        elif "Social network" in msg or "Profile" in msg:
            categories["Social Networks"].append(msg)
        elif "Summary" in msg or "summary" in msg:
            categories["Summary"].append(msg)
        elif "Skill" in msg:
            categories["Skills"].append(msg)
        elif "Project" in msg:
            categories["Projects"].append(msg)
        elif "Language" in msg:
            categories["Languages"].append(msg)
        else:
            categories["Other"].append(msg)
    return categories

# Función para ejecutar el pipeline
def run_pipeline(cv_path, job_description):
    with st.spinner("Processing your CV..."):
        try:
            os.makedirs("file_outputs", exist_ok=True)

            # Guardar la descripción del trabajo
            with open("file_outputs/job_description.txt", 'w', encoding='utf-8') as f:
                f.write(job_description)

            # Extraer datos de la oferta laboral
            job_data = extract_job_description_data(job_description, is_job=True)
            st.success("Job description data extracted")
            with open("file_outputs/job_description_data.json", 'w', encoding='utf-8') as f:
                json.dump(job_data, f, ensure_ascii=False)

            # Extraer y guardar el texto del CV
            extracted_text = extract_cv_text(cv_path)
            with open("file_outputs/extracted_cv_text.txt", 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            st.success("CV text extracted.")

            # Parsear el CV a JSON
            st.write("Standardizing CV...")
            parsed_cv = parse_to_json_resume_sync(extracted_text)
            with open("file_outputs/resume.json", 'w', encoding='utf-8') as f:
                json.dump(parsed_cv, f, ensure_ascii=False)

            cv_data = extract_job_description_data(extracted_text, is_job=False)
            st.success("Original CV standardized")

            with open("file_outputs/cv_data.json", 'w', encoding='utf-8') as f:
                json.dump(cv_data, f, ensure_ascii=False)

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
            st.subheader("Adapted CV:")
            st.json(adapted_cv)

            with open("file_outputs/adapted_cv.json", 'w', encoding='utf-8') as f:
                json.dump(adapted_cv, f, ensure_ascii=False)

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
            delta_value = adapted_score - score
            st.metric(
                label="Improvement in ATS Score",
                value=f"{adapted_score:.2f} %",
                delta=f"{delta_value:.2f} p.p",
                delta_color="normal"
            )

            # Calcular puntaje ATS antiguo
            ats_result = calculate_ats_score_old(cv_data, job_data)
            st.success("ATS analysis completed")

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
            yaml_path = convert_to_rendercv(adapted_cv, output_dir="rendercv_output", theme="classic")

            # Capturar mensajes de descarte
            discard_messages = get_discard_messages()
            st.session_state["discard_messages"] = discard_messages

            # Generate PDF
            pdf_path = generate_rendercv_pdf(yaml_path, output_dir="rendercv_output", final_pdf_name="adapted_cv.pdf")

            # Guardar los paths en session_state
            st.session_state["yaml_path"] = yaml_path
            st.session_state["pdf_path"] = pdf_path

            st.success("CV generated successfully!")

            # Mostrar mensajes de descarte en un expander
            if discard_messages:
                with st.expander("Discarded Fields", expanded=False):
                    st.markdown("### Discarded Fields")
                    st.write("The following fields were not included in the final CV due to invalid formats or missing data.")
                    organized_messages = organize_discard_messages(discard_messages)
                    for category, messages in organized_messages.items():
                        if messages:
                            st.markdown(f"**{category}**")
                            for msg in messages:
                                st.markdown(f"<div class='warning-message'>⚠️ {msg}</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# Botón para iniciar el proceso
if st.button("Generate ATS-optimized CV", use_container_width=True):
    if st.session_state["uploaded_cv_path"]:
        if st.session_state["continue_with_manual"] and st.session_state["manual_job_text"]:
            # Usar la descripción manual ya almacenada
            run_pipeline(st.session_state["uploaded_cv_path"], st.session_state["manual_job_text"])
        elif st.session_state["job_url"]:
            try:
                # Intentar scrapear la URL
                job_description = scrape_job_description(st.session_state["job_url"])
                run_pipeline(st.session_state["uploaded_cv_path"], job_description)
            except (requests.RequestException, ValueError) as e:
                st.session_state["scraping_failed"] = True
                st.warning(
                    "This website does not allow scraping. Please paste the job description manually in the input field above and try again."
                )
        else:
            st.error("Please provide a job URL or manual description.")
    else:
        st.error("Please upload a CV first.")

# Mostrar el área de texto si el scrapeo falló
if st.session_state["scraping_failed"] and not st.session_state["continue_with_manual"]:
    manual_job_text = st.text_area(
        "📝 Paste the job description here",
        placeholder="Paste the full job description (job title, responsibilities, requirements, etc.)",
        height=300,
        key="manual_job_text_input"
    )
    if st.button("Continue with Manual Description", use_container_width=True):
        if manual_job_text.strip():
            st.session_state["manual_job_text"] = manual_job_text
            st.session_state["continue_with_manual"] = True
            st.session_state["scraping_failed"] = False
            run_pipeline(st.session_state["uploaded_cv_path"], manual_job_text)
        else:
            st.error("Please provide a valid job description.")

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