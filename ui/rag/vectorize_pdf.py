import streamlit as st
from urllib.parse import urlparse
from src.vector_store.qdrant_manager import ingest_chunks_from_pdf

st.title("Add AWS Docs PDF")
st.markdown(
    "This page allows you to add a PDF from AWS documentation. The PDF will be:\n- parsed\n- vectorized and\n- stored in the vector database"
)

with st.form(key="url_form"):
    url_input = st.text_input("Enter URL:")

    submitted = st.form_submit_button("Submit")

if submitted:
    if url_input:
        parsed_url = urlparse(url_input)
        if parsed_url.scheme == "https" and "docs.aws.amazon.com" in parsed_url.netloc:
            st.toast(f"URL Valid: {url_input}")
            with st.status("Processing PDF...", expanded=True) as status:
                try:
                    total_time = ingest_chunks_from_pdf(url_input, status=status)
                    status.update(
                        label=f"PDF processed and vectorized successfully in {total_time:.2f} seconds!",
                        state="complete",
                        expanded=False,
                    )
                except Exception as e:
                    status.update(
                        label=f"An error occurred: {e}", state="error", expanded=True
                    )
    else:
        st.warning("Please enter a URL.")
