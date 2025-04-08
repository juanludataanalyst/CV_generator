import streamlit as st

st.title("CV Adapter - ATS Optimizer")

uploaded_file = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
job_url = st.text_input("Paste the job description URL")

if st.button("Generate ATS-optimized CV") and uploaded_file and job_url:
    with st.spinner("Processing..."):
        # Save uploaded PDF to disk
        with open("uploaded_cv.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Placeholder: Here the pipeline will be called
        pdf_bytes = b"PDF content here"

    st.success("Done! Download your adapted CV below.")
    st.download_button("Download adapted CV", data=pdf_bytes, file_name="Adapted_CV.pdf", mime="application/pdf")
