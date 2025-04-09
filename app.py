import streamlit as st
from pipeline import run_pipeline

st.title("CV Adapter - ATS Optimizer")

uploaded_file = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
job_url = st.text_input("Paste the job description URL")

if st.button("Generate ATS-optimized CV") and uploaded_file and job_url:
    with st.spinner("Processing..."):
        # Save uploaded PDF to disk
        with open("uploaded_cv.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Run the pipeline
        run_pipeline("uploaded_cv.pdf", job_url)

        # Read the final PDF generated
        with open("final_cv.pdf", "rb") as f:
            pdf_bytes = f.read()

    st.success("Done! Download your adapted CV below.")
    st.download_button("Download adapted CV", data=pdf_bytes, file_name="Adapted_CV.pdf", mime="application/pdf")
